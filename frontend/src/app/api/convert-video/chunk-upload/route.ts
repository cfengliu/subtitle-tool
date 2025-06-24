import { NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()

    // 轉發到 FastAPI 的 /convert/upload_chunk 端點
    const response = await ApiClient.post("/convert/upload_chunk", formData, undefined, true)

    return response
  } catch (error) {
    console.error("Error in chunk-upload route:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      },
    )
  }
} 