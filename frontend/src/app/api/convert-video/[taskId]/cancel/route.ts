import { NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function POST(request: NextRequest, { params }: { params: Promise<{ taskId: string }> }) {
  try {
    const { taskId } = await params
    
    // 转发请求到后端API
    const response = await ApiClient.post(`/convert/${taskId}/cancel`, undefined, undefined, true)
    
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