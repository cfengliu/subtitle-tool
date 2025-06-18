import { NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    
    // 使用 ApiClient 转发请求到后端API，forApiRoute=true 返回原始 Response
    const response = await ApiClient.post("/convert/", formData, undefined, true)
    
    return response
  } catch (error) {
    console.error("Error in convert-video route:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }), 
      { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
}

export async function GET() {
  try {
    // 获取活跃的转换任务列表
    const response = await ApiClient.get("/convert/tasks", undefined, true)
    
    return response
  } catch (error) {
    console.error("Error getting conversion tasks:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }), 
      { 
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
} 