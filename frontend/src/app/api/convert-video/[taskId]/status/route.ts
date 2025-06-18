import { NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

interface RouteParams {
  params: {
    taskId: string
  }
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { taskId } = params
    
    // 转发请求到后端API
    const response = await ApiClient.get(`/convert/${taskId}/status`)
    
    return response
  } catch (error) {
    console.error("Error getting conversion status:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }), 
      { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
} 