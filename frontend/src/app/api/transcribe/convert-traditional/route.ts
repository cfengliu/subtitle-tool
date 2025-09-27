import { NextRequest, NextResponse } from "next/server"

import { ApiClient } from "@/lib/api-client"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    if (typeof body?.txt === "undefined" && typeof body?.srt === "undefined") {
      return NextResponse.json(
        { detail: "No text provided for conversion" },
        { status: 400 },
      )
    }

    return ApiClient.post("/transcribe/convert-traditional", body)
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON payload" },
      { status: 400 },
    )
  }
}
