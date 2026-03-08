import { createContext, useContext, useReducer, useEffect, useState } from 'react'
import { api } from '../services/api'

// 认证状态类型
const initialState = {
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  loading: true
}

// 动作类型
const LOGIN = 'LOGIN'
const LOGOUT = 'LOGOUT'
const SET_LOADING = 'SET_LOADING'
const SET_USER = 'SET_USER'

// 状态更新函数
function authReducer(state, action) {
  switch (action.type) {
    case LOGIN:
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        loading: false
      }
    case LOGOUT:
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false
      }
    case SET_LOADING:
      return {
        ...state,
        loading: action.payload
      }
    case SET_USER:
      return {
        ...state,
        user: action.payload
      }
    default:
      return state
  }
}

// 创建上下文
const AuthContext = createContext()

// 认证提供者
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState)

  // 初始化时检查认证状态
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('token')
      if (token) {
        try {
          dispatch({ type: SET_LOADING, payload: true })
          const response = await api.get('/auth/profile')
          if (response.data.success) {
            dispatch({ type: SET_USER, payload: response.data.data })
            dispatch({ type: SET_LOADING, payload: false })
          } else {
            // 无效token，清除
            logout()
          }
        } catch (error) {
          console.error('初始化认证失败:', error)
          logout()
        }
      } else {
        dispatch({ type: SET_LOADING, payload: false })
      }
    }

    initAuth()
  }, [])

  // 登录函数
  const login = async (username, password) => {
    try {
      dispatch({ type: SET_LOADING, payload: true })
      const response = await api.post('/auth/login', {
        username,
        password
      })

      console.log('Login response:', response)

      if (response.data.success) {
        const { access_token, user } = response.data.data
        localStorage.setItem('token', access_token)
        dispatch({
          type: LOGIN,
          payload: { user, token: access_token }
        })
        dispatch({ type: SET_LOADING, payload: false })
        return { success: true, user }
      } else {
        dispatch({ type: SET_LOADING, payload: false })
        return { success: false, error: response.data.message || response.data.error || '登录失败' }
      }
    } catch (error) {
      dispatch({ type: SET_LOADING, payload: false })
      console.error('Login error:', error)

      let errorMsg = '网络错误'
      if (error.response) {
        errorMsg = error.response.data.error || error.response.data.message || `HTTP ${error.response.status}`
      } else if (error.request) {
        errorMsg = '服务器无响应'
      } else {
        errorMsg = error.message
      }

      return {
        success: false,
        error: errorMsg
      }
    }
  }

  // 注册函数
  const register = async (username, password, email = null, phone = null) => {
    try {
      dispatch({ type: SET_LOADING, payload: true })
      const response = await api.post('/auth/register', {
        username,
        password,
        email,
        phone
      })

      console.log('Register response:', response)

      if (response.data.success) {
        const { access_token, user } = response.data.data
        localStorage.setItem('token', access_token)
        dispatch({
          type: LOGIN,
          payload: { user, token: access_token }
        })
        dispatch({ type: SET_LOADING, payload: false })
        return { success: true, user }
      } else {
        dispatch({ type: SET_LOADING, payload: false })
        return { success: false, error: response.data.message || response.data.error || '注册失败' }
      }
    } catch (error) {
      dispatch({ type: SET_LOADING, payload: false })
      console.error('Register error:', error)

      let errorMsg = '网络错误'
      if (error.response) {
        errorMsg = error.response.data.error || error.response.data.message || `HTTP ${error.response.status}`
      } else if (error.request) {
        errorMsg = '服务器无响应'
      } else {
        errorMsg = error.message
      }

      return {
        success: false,
        error: errorMsg
      }
    }
  }

  // 登出函数
  const logout = async () => {
    try {
      const token = localStorage.getItem('token')
      if (token) {
        await api.post('/auth/logout')
      }
    } catch (error) {
      // 登出接口失败也要继续清理本地状态
    } finally {
      localStorage.removeItem('token')
      dispatch({ type: LOGOUT })
    }
  }

  // 注销账号
  const deleteAccount = async () => {
    try {
      const response = await api.delete('/users/account')
      if (response.data.success) {
        logout()
        return { success: true }
      }
      return { success: false, error: response.data.error || '注销失败' }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '网络错误'
      }
    }
  }

  // 更新用户信息
  const updateProfile = async (userData) => {
    try {
      const response = await api.put('/users/profile', userData)
      if (response.data.success) {
        dispatch({ type: SET_USER, payload: response.data.data })
        return { success: true, user: response.data.data }
      }
      return { success: false, error: response.data.error }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '网络错误'
      }
    }
  }

  // 更新用户设置
  const updateSettings = async (settings) => {
    try {
      const response = await api.put('/users/settings', settings)
      if (response.data.success) {
        // 更新用户信息
        const profileResponse = await api.get('/auth/profile')
        if (profileResponse.data.success) {
          dispatch({ type: SET_USER, payload: profileResponse.data.data })
        }
        return { success: true }
      }
      return { success: false, error: response.data.error }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '网络错误'
      }
    }
  }

  // 上传头像
  const uploadAvatar = async (file) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post('/users/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (response.data.success) {
        // 更新用户信息
        const profileResponse = await api.get('/auth/profile')
        if (profileResponse.data.success) {
          dispatch({ type: SET_USER, payload: profileResponse.data.data })
        }
        return { success: true, avatar: response.data.data.avatar }
      }
      return { success: false, error: response.data.error }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || '网络错误'
      }
    }
  }

  // 获取用户资料和魅力值信息
  const fetchUserProfile = async () => {
    try {
      const response = await api.get('/auth/profile')
      if (response.data.success) {
        dispatch({ type: SET_USER, payload: response.data.data })
        return response.data.data
      }
      return null
    } catch (error) {
      console.error('获取用户信息失败:', error)
      return null
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
        loading: state.loading,
        login,
        register,
        logout,
        deleteAccount,
        updateProfile,
        updateSettings,
        uploadAvatar,
        fetchUserProfile
      }}
    >
      {!state.loading && children}
    </AuthContext.Provider>
  )
}

// 自定义Hook用于访问认证上下文
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
