import { NextRequest } from "next/server"

const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

export async function GET(request: NextRequest, { params }: { params: Promise<{ taskId: string }> }) {
  try {
    const { taskId } = await params

    const response = await fetch(`${API_BASE_URL}/convert/${taskId}/download`)

    if (!response.ok) {
      // Pass through error response
      const errorText = await response.text()
      return new Response(errorText, {
        status: response.status,
        headers: {
          "Content-Type": response.headers.get("content-type") || "application/json"
        }
      })
    }

    // Forward file stream and headers
    const headers: HeadersInit = {
      "Content-Type": response.headers.get("content-type") || "audio/mpeg",
      "Content-Disposition": response.headers.get("content-disposition") || "attachment"
    }

    const arrayBuffer = await response.arrayBuffer()
    return new Response(arrayBuffer, {
      status: 200,
      headers
    })
  } catch (error) {
    console.error("Error proxying download request:", error)
    return new Response(
      JSON.stringify({ detail: "Internal server error" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" }
      }
    )
  }
} 