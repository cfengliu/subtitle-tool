import { type NextRequest } from "next/server"
import { ApiClient } from "@/lib/api-client"

export async function GET(request: NextRequest) {
  return ApiClient.get("/health")
}
