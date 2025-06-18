import { type NextRequest, NextResponse } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await params
  return ApiClient.post(`/transcribe/${taskId}/cancel`)
} 