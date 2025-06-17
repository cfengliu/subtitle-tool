import { type NextRequest, NextResponse } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function POST(request: NextRequest) {
  const formData = await request.formData()
  const file = formData.get("file") as File
  const language = formData.get("language") as string

  if (!file) {
    return NextResponse.json(
      { detail: [{ loc: ["body", "file"], msg: "File is required", type: "missing" }] },
      { status: 422 },
    )
  }

  // Create FormData for the external API
  const apiFormData = new FormData()
  apiFormData.append("file", file)
  
  // Add language parameter if provided
  if (language && language.trim() !== "") {
    apiFormData.append("language", language)
  }

  return ApiClient.post("/transcribe/", apiFormData)
}
