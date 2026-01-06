interface InternalUser {
  id: string
  username: string
  password: string
  role: string
}

const memoryUsers = new Map<string, InternalUser>()
const tokens = new Map<string, string>()

const seed = () => {
  if (memoryUsers.size === 0) {
    memoryUsers.set('admin', {
      id: 'u-1',
      username: 'admin',
      password: 'admin123',
      role: 'admin'
    })
  }
}

const issueToken = (username: string) => {
  const token = `mock-${Date.now()}-${Math.random().toString(16).slice(2)}`
  tokens.set(token, username)
  return token
}

const sanitize = (user: InternalUser) => ({ id: user.id, username: user.username, role: user.role })

export const loginUser = (username: string, password: string) => {
  seed()
  const user = memoryUsers.get(username)
  if (!user || user.password !== password) return { error: '用户名或密码错误' }
  const token = issueToken(username)
  return { user: sanitize(user), token }
}

export const registerUser = (username: string, password: string) => {
  seed()
  if (memoryUsers.has(username)) return { error: '用户已存在' }
  const id = `u-${memoryUsers.size + 1}`
  const user: InternalUser = { id, username, password, role: 'user' }
  memoryUsers.set(username, user)
  const token = issueToken(username)
  return { user: sanitize(user), token }
}

export const findByToken = (token?: string | null) => {
  seed()
  if (!token) return null
  const username = tokens.get(token)
  if (!username) return null
  const user = memoryUsers.get(username)
  return user ? sanitize(user) : null
}
