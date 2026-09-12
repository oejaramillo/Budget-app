import { createResourceHooks } from './createResourceHooks'
import {
  createCategory,
  deleteCategory,
  fetchCategories,
  updateCategory,
} from '../services/categoriesService'

/** Categories list plus mutations. */
export const useCategories = createResourceHooks({
  resource: 'categories',
  list: fetchCategories,
  create: createCategory,
  update: updateCategory,
  remove: deleteCategory,
})
