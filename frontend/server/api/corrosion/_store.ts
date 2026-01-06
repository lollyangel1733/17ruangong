import type { H3Event } from 'h3'
import { getCookie, getHeader } from 'h3'
import { Buffer } from 'buffer'
import { findByToken } from '../auth/_store'

export interface DetectParams {
  model: string
  conf: number
  iou: number
  imgsz: number
  max_det: number
}

export interface DetectionMetrics {
  count: number
  area_ratio: number
  avg_conf: number
}

export interface DetectionRecord {
  id: string
  userId: string
  username: string
  filename: string
  params: DetectParams
  metrics: DetectionMetrics
  image_base64: string
  created_at: string
}

export type JobStatus = 'queued' | 'running' | 'done' | 'error'

export interface JobRecord {
  id: string
  userId: string
  username: string
  status: JobStatus
  result?: DetectionRecord
  message?: string
}

const detectionStore = new Map<string, DetectionRecord[]>()
const jobStore = new Map<string, JobRecord>()

export const readUserFromEvent = (event: H3Event) => {
  const authHeader = getHeader(event, 'authorization') || ''
  if (authHeader.toLowerCase().startsWith('bearer ')) {
    const token = authHeader.slice(7)
    const user = findByToken(token)
    if (user) return user
  }
  const cookieToken = getCookie(event, 'auth_token')
  if (cookieToken) {
    const user = findByToken(cookieToken)
    if (user) return user
  }
  return null
}

const toBase64 = (data: Buffer | Uint8Array) => {
  const buf = data instanceof Buffer ? data : Buffer.from(data)
  return buf.toString('base64')
}

const makeId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

export const createMockDetection = (userId: string, username: string, file: { data: Buffer | Uint8Array; filename?: string }, params: DetectParams): DetectionRecord => {
  const metrics: DetectionMetrics = {
    count: 1,
    area_ratio: 0.12,
    avg_conf: Number((params.conf || 0.5).toFixed(3))
  }
  const record: DetectionRecord = {
    id: makeId(),
    userId,
    username,
    filename: file.filename || 'upload.png',
    params,
    metrics,
    image_base64: toBase64(file.data),
    created_at: new Date().toISOString()
  }
  const list = detectionStore.get(userId) || []
  list.unshift(record)
  detectionStore.set(userId, list.slice(0, 200))
  return record
}

export const createMockJob = (userId: string, username: string, file: { data: Buffer | Uint8Array; filename?: string }, params: DetectParams): JobRecord => {
  const job: JobRecord = { id: makeId(), userId, username, status: 'done' }
  const detection = createMockDetection(userId, username, file, params)
  job.status = 'done'
  job.result = detection
  jobStore.set(job.id, job)
  return job
}

export const getJobById = (jobId: string, userId: string) => {
  const job = jobStore.get(jobId)
  if (!job) return null
  if (job.userId !== userId) return null
  return job
}
