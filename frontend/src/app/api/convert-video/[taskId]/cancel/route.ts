import { NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

interface RouteParams {
  params: {
    taskId: string
  }
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const { taskId } = params
    
    // 转发请求到后端API
    const response = await ApiClient.post(`/convert/${taskId}/cancel`)
    
    return response
  } catch (error) {
    console.error("Error cancelling conversion:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }), 
      { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
} 