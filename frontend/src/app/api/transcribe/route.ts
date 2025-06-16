import { type NextRequest, NextResponse } from "next/server"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const file = formData.get("file") as File

    if (!file) {
      return NextResponse.json(
        { detail: [{ loc: ["body", "file"], msg: "File is required", type: "missing" }] },
        { status: 422 },
      )
    }

    // Create FormData for the external API
    const apiFormData = new FormData()
    apiFormData.append("file", file)

    // Replace with your actual API endpoint
    const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

    const response = await fetch(`${API_BASE_URL}/transcribe/`, {
      method: "POST",
      body: apiFormData,
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const result = await response.json()
    return NextResponse.json(result)
  } catch (error) {
    console.error("Transcription error:", error)
    return NextResponse.json(
      { detail: [{ loc: ["server"], msg: "Internal server error", type: "server_error" }] },
      { status: 500 },
    )
  }
}
