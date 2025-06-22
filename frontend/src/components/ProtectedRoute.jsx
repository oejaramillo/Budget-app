//wrapper for protected, route, if something is wrapped here, we need an authorization token 
import { Navigate } from 'react-router-dom'
import { jwtDecode } from 'jwt-decode'
import api from '../api'
import { ACCESS_TOKEN, REFRESH_TOKEN } from '../constants'
import { useState, useEffect } from 'react'

function ProtectedRoute({ children }) {
   const [isAuthorized, setIsAuthorize] = useState(null)

   useEffect(() => {
       auth().catch(() => setIsAuthorize(false))
   }, [])
    
   const refreshToken = async () => {
       const refreshToken = localStorage.getItem(REFRESH_TOKEN)

       try {
           const res = await api.post('/api/token/refresh', { 
               refresh: refreshToken 
           });
           if (res.status === 200) { 
               localStorage.setItem(ACCESS_TOKEN, res.data.access)
               setIsAuthorize(true)
           } else  {
               setIsAuthorize(false)
           }
       } catch (error) {
           console.log(error)
           setIsAuthorize(false)
       };
        
   }


   const auth = async () => {
       const accessToken = localStorage.getItem(ACCESS_TOKEN)
       if (!accessToken) {
           setIsAuthorize(false)
           return
       }
       const decoded = jwtDecode(accessToken)
       const tokenExp = decoded.exp
       const currentTime = Date.now() / 1000

       if (tokenExp < currentTime) {
           await refreshToken()
       } else {
           setIsAuthorize(true)
       }   
    }

    if (isAuthorized === null) {
        return <div>Loading...</div>
    }
    
    return isAuthorized ? children : <Navigate to="/login" />

}
 
export default ProtectedRoute