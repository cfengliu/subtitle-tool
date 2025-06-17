import { NextResponse } from "next/server"

const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

interface ApiRequestOptions {
  method: "GET" | "POST" | "PUT" | "DELETE"
  body?: FormData | Record<string, any>
  headers?: Record<string, string>
}

export class ApiClient {
  private static async makeRequest(endpoint: string, options: ApiRequestOptions) {
    try {
      const url = `${API_BASE_URL}${endpoint}`
      
      const fetchOptions: RequestInit = {
        method: options.method,
        headers: options.headers,
      }

      if (options.body) {
        if (options.body instanceof FormData) {
          fetchOptions.body = options.body
        } else {
          fetchOptions.headers = {
            "Content-Type": "application/json",
            ...options.headers,
          }
          fetchOptions.body = JSON.stringify(options.body)
        }
      }

      const response = await fetch(url, fetchOptions)

      if (!response.ok) {
        const errorData = await response.json()
        return NextResponse.json(errorData, { status: response.status })
      }

      const result = await response.json()
      return NextResponse.json(result)
    } catch (error) {
      console.error(`API request error for ${endpoint}:`, error)
      return NextResponse.json(
        { detail: [{ loc: ["server"], msg: "Internal server error", type: "server_error" }] },
        { status: 500 },
      )
    }
  }

  static async get(endpoint: string, headers?: Record<string, string>) {
    return this.makeRequest(endpoint, { method: "GET", headers })
  }

  static async post(endpoint: string, body?: FormData | Record<string, any>, headers?: Record<string, string>) {
    return this.makeRequest(endpoint, { method: "POST", body, headers })
  }

  static async put(endpoint: string, body?: FormData | Record<string, any>, headers?: Record<string, string>) {
    return this.makeRequest(endpoint, { method: "PUT", body, headers })
  }

  static async delete(endpoint: string, headers?: Record<string, string>) {
    return this.makeRequest(endpoint, { method: "DELETE", headers })
  }
} 