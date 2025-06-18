import React, { useRef, useState, useEffect } from "react"
import * as lamejs from "@breezystack/lamejs"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface AudioCutterProps {
  file: File
  onCut: (cutFile: File) => void
}

const AudioCutter: React.FC<AudioCutterProps> = ({ file, onCut }) => {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [duration, setDuration] = useState<number>(0)
  const [startTime, setStartTime] = useState<number>(0)
  const [endTime, setEndTime] = useState<number | null>(null)
  const [cutting, setCutting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [audioUrl, setAudioUrl] = useState<string>("")

  useEffect(() => {
    const url = URL.createObjectURL(file)
    setAudioUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      const audioDuration = Math.floor(audioRef.current.duration)
      setDuration(audioRef.current.duration)
      setEndTime(audioDuration)
    }
  }

  const handleCut = async () => {
    setError(null)
    if (endTime === null || endTime <= startTime) {
      setError("結束時間必須大於開始時間")
      return
    }
    setCutting(true)
    try {
      // 讀取檔案為 ArrayBuffer
      const arrayBuffer = await file.arrayBuffer()
      // 用 Web Audio API decode
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      const audioCtx = new AudioCtx()
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer.slice(0))
      // 計算裁切範圍
      const sampleRate = audioBuffer.sampleRate
      const startSample = Math.floor(startTime * sampleRate)
      const endSample = Math.floor(endTime * sampleRate)
      const length = endSample - startSample
      // 只取第一個聲道
      const channelData = audioBuffer.getChannelData(0).slice(startSample, endSample)
      // MP3 編碼
      const mp3Encoder = new lamejs.Mp3Encoder(1, sampleRate, 128)
      const samples = new Int16Array(channelData.length)
      for (let i = 0; i < channelData.length; i++) {
        samples[i] = Math.max(-32768, Math.min(32767, channelData[i] * 32767))
      }
      const mp3Data: Uint8Array[] = []
      let remaining = samples.length
      const maxSamples = 1152
      for (let i = 0; remaining >= maxSamples; i += maxSamples) {
        const mono = samples.subarray(i, i + maxSamples)
        const mp3buf = mp3Encoder.encodeBuffer(mono)
        if (mp3buf.length > 0) {
          mp3Data.push(new Uint8Array(mp3buf))
        }
        remaining -= maxSamples
      }
      const mp3buf = mp3Encoder.flush()
      if (mp3buf.length > 0) {
        mp3Data.push(new Uint8Array(mp3buf))
      }
      // 合併 mp3Data
      const blob = new Blob(mp3Data, { type: "audio/mp3" })
      const cutFile = new File([blob], `cut_${file.name.replace(/\.[^/.]+$/, "")}.mp3`, { type: "audio/mp3" })
      
      // 計算新音檔的長度並重置時間（只保留整數）
      const newDuration = Math.floor(endTime - startTime)
      setStartTime(0)
      setEndTime(newDuration)
      setDuration(newDuration)
      
      onCut(cutFile)
    } catch (err) {
      setError("裁切失敗，請確認音檔格式或重試。")
    } finally {
      setCutting(false)
    }
  }

  return (
    <div className="space-y-3">
      <audio
        ref={audioRef}
        src={audioUrl}
        controls
        onLoadedMetadata={handleLoadedMetadata}
        className="w-full"
      />
      <div className="flex gap-2 items-center">
        <Label className="text-xs">開始時間(秒):</Label>
        <Input
          type="number"
          min={0}
          max={endTime ?? undefined}
          value={startTime}
          onChange={e => setStartTime(Number(e.target.value))}
          className="w-24"
        />
        <Label className="text-xs">結束時間(秒):</Label>
        <Input
          type="number"
          min={startTime}
          max={duration}
          value={endTime ?? ""}
          onChange={e => setEndTime(Number(e.target.value))}
          className="w-24"
        />
        <Button onClick={handleCut} disabled={cutting} type="button">
          {cutting ? "裁切中..." : "裁切並取代音檔"}
        </Button>
      </div>
      {error && <div className="text-red-500 text-xs">{error}fdfjsd</div>}
      <div className="text-xs text-muted-foreground">音檔長度: {duration.toFixed(2)} 秒</div>
    </div>
  )
}

export default AudioCutter 