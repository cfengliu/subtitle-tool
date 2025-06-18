import { NextRequest } from "next/server"

const API_BASE_URL = process.env.TRANSCRIPTION_API_URL || "http://localhost:8010"

export async function GET(request: NextRequest, { params }: { params: Promise<{ taskId: string }> }) {
  try {
    const { taskId } = await params
    
    // 直接从后端API获取音频文件
    const response = await fetch(`${API_BASE_URL}/convert/${taskId}/result`)
    
    if (!response.ok) {
      if (response.status === 404) {
        return new Response(
          JSON.stringify({ detail: "任务不存在" }), 
          { 
            status: 404,
            headers: { "Content-Type": "application/json" }
          }
        )
      }
      if (response.status === 202) {
        return new Response(
          JSON.stringify({ detail: "任务仍在进行中" }), 
          { 
            status: 202,
            headers: { "Content-Type": "application/json" }
          }
        )
      }
      if (response.status === 410) {
        return new Response(
          JSON.stringify({ detail: "任务已被取消" }), 
          { 
            status: 410,
            headers: { "Content-Type": "application/json" }
          }
        )
      }
      if (response.status === 500) {
        return new Response(
          JSON.stringify({ detail: "任务执行失败" }), 
          { 
            status: 500,
            headers: { "Content-Type": "application/json" }
          }
        )
      }
      
      const errorData = await response.json()
      return new Response(
        JSON.stringify(errorData), 
        { 
          status: response.status,
          headers: { "Content-Type": "application/json" }
        }
      )
    }
    
    // 获取音频数据
    const audioBuffer = await response.arrayBuffer()
    const contentType = response.headers.get("content-type") || "audio/mpeg"
    const contentDisposition = response.headers.get("content-disposition") || "attachment; filename=converted_audio.mp3"
    
    return new Response(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": contentDisposition,
        "Content-Length": audioBuffer.byteLength.toString()
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