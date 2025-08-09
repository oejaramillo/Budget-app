import api from '../api'

export const fetchAccounts = () => {
    return api.get('/api/accounts/')
};
export const createAccount = (data) => {
    return api.post('/api/accounts/', data)
};
export const deleteAccount = (id: number) => {
    return api.delete(`/api/accounts/${id}/`)
};