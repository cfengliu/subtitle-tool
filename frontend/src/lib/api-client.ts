import { NextResponse } from "next/server"

const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

interface ApiRequestOptions {
  method: "GET" | "POST" | "PUT" | "DELETE"
  body?: FormData | Record<string, unknown>
  headers?: Record<string, string>
}

export class ApiClient {
  private static async makeRequest(endpoint: string, options: ApiRequestOptions, returnRawResponse = false) {
    try {
      const url = `${API_BASE_URL}${endpoint}`
      
      const fetchOptions: RequestInit = {
        method: options.method,
        headers: options.headers,
      }

      if (options.body) {
        if (options.body instanceof FormData) {
          fetchOptions.body = options.body
          // 不要手動設置 Content-Type，讓瀏覽器自動設置 multipart/form-data 邊界
        } else {
          fetchOptions.headers = {
            "Content-Type": "application/json",
            ...options.headers,
          }
          fetchOptions.body = JSON.stringify(options.body)
        }
      }

      const response = await fetch(url, fetchOptions)

      // 如果需要原始 Response（用於 API 路由轉發）
      if (returnRawResponse) {
        if (!response.ok) {
          const errorData = await response.json()
          return new Response(
            JSON.stringify(errorData), 
            { 
              status: response.status,
              headers: { "Content-Type": "application/json" }
            }
          )
        }

        const result = await response.json()
        return new Response(
          JSON.stringify(result), 
          { 
            status: 200,
            headers: { "Content-Type": "application/json" }
          }
        )
      }

      // 默認返回 NextResponse（用於前端組件）
      if (!response.ok) {
        const errorData = await response.json()
        return NextResponse.json(errorData, { status: response.status })
      }

      const result = await response.json()
      return NextResponse.json(result)
    } catch (error) {
      console.error(`API request error for ${endpoint}:`, error)
      
      if (returnRawResponse) {
        return new Response(
          JSON.stringify({ detail: "Internal server error" }), 
          { 
            status: 500,
            headers: { "Content-Type": "application/json" }
          }
        )
      }
      
      return NextResponse.json(
        { detail: [{ loc: ["server"], msg: "Internal server error", type: "server_error" }] },
        { status: 500 },
      )
    }
  }

  static async get(endpoint: string, headers?: Record<string, string>, forApiRoute = false) {
    return this.makeRequest(endpoint, { method: "GET", headers }, forApiRoute)
  }

  static async post(endpoint: string, body?: FormData | Record<string, unknown>, headers?: Record<string, string>, forApiRoute = false) {
    return this.makeRequest(endpoint, { method: "POST", body, headers }, forApiRoute)
  }

  static async put(endpoint: string, body?: FormData | Record<string, unknown>, headers?: Record<string, string>, forApiRoute = false) {
    return this.makeRequest(endpoint, { method: "PUT", body, headers }, forApiRoute)
  }

  static async delete(endpoint: string, headers?: Record<string, string>, forApiRoute = false) {
    return this.makeRequest(endpoint, { method: "DELETE", headers }, forApiRoute)
  }
} 