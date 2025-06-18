import { ApiClient } from "@/lib/api-client"

export async function GET() {
  return ApiClient.get("/health")
}
