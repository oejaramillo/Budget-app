import { useState } from 'react'
import axios from 'axios'

/**
 * Tiny form controller for the resource forms.
 *
 * Handles:
 *  - controlled values with a single `setField` / `handleChange`;
 *  - resetting when the record being edited changes;
 *  - mapping DRF validation errors (`{field: ["message"]}`) onto the right field;
 *  - a submit guard so the button can be disabled while a mutation is in flight.
 *
 * @param {Object} options
 * @param {Record<string, any>} options.initialValues
 * @param {(values: any) => Promise<any>} options.onSubmit
 * @param {(result: any) => void} [options.onSuccess]
 */
export function useForm({ initialValues, onSubmit, onSuccess }) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const setField = (name, value) => {
    setValues((previous) => ({ ...previous, [name]: value }))
    // Clear a field error as soon as the user edits that field.
    setErrors((previous) => {
      if (!previous[name]) return previous
      const next = { ...previous }
      delete next[name]
      return next
    })
  }

  const handleChange = (event) => {
    const { name, type, value, checked } = event.target
    if (type === 'checkbox') {
      setField(name, checked)
      return
    }
    if (type === 'number') {
      setField(name, value === '' ? '' : value)
      return
    }
    setField(name, value)
  }

  const reset = (nextValues = initialValues) => {
    setValues(nextValues)
    setErrors({})
    setFormError('')
  }

  const handleSubmit = async (event) => {
    if (event) event.preventDefault()
    setIsSubmitting(true)
    setErrors({})
    setFormError('')

    try {
      const result = await onSubmit(values)
      if (onSuccess) onSuccess(result)
      return result
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const data = error.response.data
        if (typeof data === 'object' && !Array.isArray(data)) {
          const fieldErrors = {}
          Object.entries(data).forEach(([field, messages]) => {
            if (field === 'detail' || field === 'non_field_errors') {
              fieldErrors._form = Array.isArray(messages) ? messages.join(' ') : String(messages)
            } else {
              fieldErrors[field] = Array.isArray(messages) ? messages.join(' ') : String(messages)
            }
          })
          setErrors(fieldErrors)
        } else {
          setFormError(String(data))
        }
      } else {
        setFormError(error?.message ?? 'Something went wrong.')
      }
      return null
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    values,
    errors,
    formError,
    isSubmitting,
    setField,
    setValues,
    setErrors,
    setFormError,
    handleChange,
    handleSubmit,
    reset,
  }
}
