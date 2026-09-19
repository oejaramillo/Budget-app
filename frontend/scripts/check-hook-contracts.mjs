#!/usr/bin/env node
/**
 * Contract check: a data hook and its consumers must agree on the name of the list.
 *
 * This guards a bug that shipped. `createResourceHooks` returned its rows under a
 * generic `items`, while every manager destructured the resource name — so
 * `accounts` was `undefined` and the screen crashed with
 * "Cannot read properties of undefined (reading 'length')". Neither eslint nor
 * `vite build` complains about destructuring a property that does not exist, and a
 * component test would only have covered the screens it happened to render.
 *
 * Three assertions, all of them about names:
 *
 *  1. `createResourceHooks` must publish the list as `[listKey]`, computed from the
 *     `resource` option. A generic key breaks every consumer at once.
 *  2. Every data hook must expose the list under the name its consumers read.
 *  3. No consumer may destructure a property its hook does not expose.
 *
 * Run with `npm run check:contracts`.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))
const problems = []

/** hook name -> the property its consumers read for the list of rows. */
const LIST_PROPERTY = {
  useAccounts: 'accounts',
  useBudgets: 'budgets',
  useCategories: 'categories',
  useCurrencies: 'currencies',
  useHoldings: 'holdings',
  useTransactions: 'transactions',
}

/** hook name -> defining file, when it differs from the hook name. */
const HOOK_FILE = { useHoldings: 'useInvestments' }

/** Members a factory-built hook returns in addition to the list. */
const FACTORY_MEMBERS = [
  'isLoading',
  'isError',
  'isPending',
  'isSuccess',
  'error',
  'refetch',
  'create',
  'update',
  'remove',
  'reset',
  'mutate',
  'mutateAsync',
]

const hookPath = (hookName) => join(SRC, 'hooks', `${HOOK_FILE[hookName] ?? hookName}.js`)

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry)
    return statSync(full).isDirectory() ? walk(full) : [full]
  })
}

/** Properties a hook's returned object literal contains, plus factory members. */
function exposedProperties(hookName) {
  const source = readFileSync(hookPath(hookName), 'utf8')
  const exposed = new Set()

  for (const [, body] of source.matchAll(/return\s*\{([\s\S]*?)\n\s{0,6}\}/g)) {
    for (const line of body.split('\n')) {
      const trimmed = line.trim().replace(/,$/, '')
      const withValue = trimmed.match(/^\[?([a-zA-Z_$][\w$]*)\]?\s*:/)
      if (withValue) {
        exposed.add(withValue[1])
        continue
      }
      const shorthand = trimmed.match(/^([a-zA-Z_$][\w$]*)$/)
      if (shorthand) exposed.add(shorthand[1])
    }
  }

  const resourceMatch = source.match(/resource:\s*'([^']+)'/)
  if (resourceMatch && /createResourceHooks\(/.test(source)) {
    // A factory hook's object literal lives in createResourceHooks.js; its list key
    // is the resource name passed here.
    exposed.add(resourceMatch[1])
    FACTORY_MEMBERS.forEach((member) => exposed.add(member))
  }

  return exposed
}

// -- 1. The factory must publish the list under the computed resource name -----

const factorySource = readFileSync(join(SRC, 'hooks', 'createResourceHooks.js'), 'utf8')
if (!/\[listKey\]:\s*query\.data/.test(factorySource)) {
  problems.push(
    'createResourceHooks.js does not expose the list as `[listKey]: query.data ?? []`; ' +
      'a generic key leaves every consumer reading `undefined`.'
  )
}
if (!/const listKey =/.test(factorySource)) {
  problems.push('createResourceHooks.js does not derive `listKey` from the resource name.')
}

// -- 2. Every hook must expose the name its consumers read ---------------------

for (const [hookName, listProperty] of Object.entries(LIST_PROPERTY)) {
  const exposed = exposedProperties(hookName)
  if (!exposed.has(listProperty)) {
    problems.push(
      `${hookName}() does not expose '${listProperty}'. Exposes: ` +
        `${[...exposed].sort().join(', ') || '(nothing)'}`
    )
  }
}

// -- 3. Consumers must not read properties the hook does not expose -----------

const consumers = walk(join(SRC, 'components')).filter((file) => /\.jsx?$/.test(file))
const DESTRUCTURE = /const\s*\{([^}]+)\}\s*=\s*(use[A-Z][A-Za-z]*)\s*\(/g

for (const file of consumers) {
  const source = readFileSync(file, 'utf8')

  for (const [, rawNames, hookName] of source.matchAll(DESTRUCTURE)) {
    if (!(hookName in LIST_PROPERTY)) continue // not a data hook; out of scope

    const exposed = exposedProperties(hookName)
    const names = rawNames
      .split(',')
      .map((part) => part.trim().split(':')[0].trim())
      .filter(Boolean)

    for (const name of names) {
      if (exposed.has(name)) continue
      problems.push(
        `${relative(SRC, file)} reads '${name}' from ${hookName}(), which exposes: ` +
          `${[...exposed].sort().join(', ')}`
      )
    }
  }
}

if (problems.length) {
  console.error('Hook/consumer contract violations:\n')
  for (const problem of problems) console.error(`  x ${problem}`)
  console.error(
    '\nA hook exposes its rows under its resource name; consumers must read that name.'
  )
  process.exit(1)
}

console.log(
  `Hook contracts OK (${Object.keys(LIST_PROPERTY).length} data hooks, ` +
    `${consumers.length} components checked).`
)
