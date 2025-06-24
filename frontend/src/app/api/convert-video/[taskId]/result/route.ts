import { NextRequest } from "next/server"

const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

export async function GET(request: NextRequest, { params }: { params: Promise<{ taskId: string }> }) {
  try {
    const { taskId } = await params

    // Request JSON result from backend
    const response = await fetch(`${API_BASE_URL}/convert/${taskId}/result`)

    // Pass through status code and payload
    const contentType = response.headers.get("content-type") || "application/json"
    const data = await response.text()

    return new Response(data, {
      status: response.status,
      headers: {
        "Content-Type": contentType
      }
    })
  } catch (error) {
    console.error("Error getting conversion result:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
} 