"use client"

import type React from "react"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { 
  FileVideo, 
  FileAudio, 
  ArrowRight,
  Info,
  Zap,
  Shield,
  Download
} from "lucide-react"
import VideoToAudio from "@/components/VideoToAudio"

export default function VideoConverterPage() {
  const [convertedAudio, setConvertedAudio] = useState<File | null>(null)

  const handleAudioGenerated = (audioFile: File) => {
    setConvertedAudio(audioFile)
  }

  const features = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: "高效轉換",
      description: "使用專業的 FFmpeg 引擎，提供高品質的音頻轉換"
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: "穩定可靠",
      description: "後端處理確保轉換穩定性，支持大文件處理"
    },
    {
      icon: <FileAudio className="w-6 h-6" />,
      title: "多格式支持",
      description: "支持輸出 MP3、WAV、OGG 等常見音頻格式"
    },
    {
      icon: <Download className="w-6 h-6" />,
      title: "品質選擇",
      description: "提供高、中、低三種品質選項，滿足不同需求"
    }
  ]

  const supportedFormats = {
    input: ["MP4", "AVI", "MOV", "MKV", "WMV", "FLV", "WEBM"],
    output: ["MP3", "WAV", "OGG"]
  }

  return (
    <>
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">影片轉音頻工具</h1>
        <p className="text-muted-foreground">專業的影片轉音頻工具，支持多種格式轉換</p>
      </div>

      <Tabs defaultValue="converter" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="converter">轉換工具</TabsTrigger>
          <TabsTrigger value="features">功能特色</TabsTrigger>
          <TabsTrigger value="help">使用說明</TabsTrigger>
        </TabsList>

        <TabsContent value="converter" className="space-y-6">
          <VideoToAudio onAudioGenerated={handleAudioGenerated} />
          
          {convertedAudio && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileAudio className="w-5 h-5" />
                  轉換完成
                </CardTitle>
                <CardDescription>您的音頻文件已準備就緒</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 p-4 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-800">
                  <div className="flex items-center gap-2">
                    <FileAudio className="w-5 h-5 text-green-600" />
                    <span className="font-medium">{convertedAudio.name}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                  <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    轉換成功
                  </Badge>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="features" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {features.map((feature, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg text-primary">
                      {feature.icon}
                    </div>
                    {feature.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="w-5 h-5" />
                支持的文件格式
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <FileVideo className="w-4 h-4" />
                    輸入格式（影片）
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {supportedFormats.input.map((format) => (
                      <Badge key={format} variant="outline">
                        {format}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <FileAudio className="w-4 h-4" />
                    輸出格式（音頻）
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {supportedFormats.output.map((format) => (
                      <Badge key={format} variant="outline">
                        {format}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="help" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>使用步驟</CardTitle>
              <CardDescription>按照以下步驟輕鬆轉換您的影片文件</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">
                    1
                  </div>
                  <div>
                    <h4 className="font-medium">選擇影片文件</h4>
                    <p className="text-sm text-muted-foreground">點擊上傳區域或直接拖拽影片文件到頁面中</p>
                  </div>
                </div>
                
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">
                    2
                  </div>
                  <div>
                    <h4 className="font-medium">設定轉換參數</h4>
                    <p className="text-sm text-muted-foreground">選擇輸出的音頻格式（MP3、WAV、OGG）和品質等級</p>
                  </div>
                </div>
                
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">
                    3
                  </div>
                  <div>
                    <h4 className="font-medium">開始轉換</h4>
                    <p className="text-sm text-muted-foreground">點擊「開始轉換」按鈕，等待處理完成</p>
                  </div>
                </div>
                
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">
                    4
                  </div>
                  <div>
                    <h4 className="font-medium">下載結果</h4>
                    <p className="text-sm text-muted-foreground">轉換完成後，可以預覽音頻並下載到您的設備</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>常見問題</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium mb-1">轉換需要多長時間？</h4>
                  <p className="text-sm text-muted-foreground">
                    轉換時間取決於影片長度和文件大小。通常情況下，轉換速度很快，大部分文件在幾分鐘內完成。
                  </p>
                </div>
                
                <div>
                  <h4 className="font-medium mb-1">文件大小有限制嗎？</h4>
                  <p className="text-sm text-muted-foreground">
                    支持處理大文件，具體大小限制取決於伺服器配置。一般情況下支持 GB 級別的影片文件。
                  </p>
                </div>
                
                <div>
                  <h4 className="font-medium mb-1">我的文件安全嗎？</h4>
                  <p className="text-sm text-muted-foreground">
                    文件處理完成後會自動清理，不會長期保存在伺服器上，確保您的隱私安全。
                  </p>
                </div>
                
                <div>
                  <h4 className="font-medium mb-1">支持哪些格式？</h4>
                  <p className="text-sm text-muted-foreground">
                    支持大部分常見的影片格式輸入，包括 MP4、AVI、MOV、MKV 等，輸出支援 MP3、WAV、OGG 格式。
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
    </>
  )
} 