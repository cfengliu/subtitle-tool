"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { FileAudio, FileVideo, Home } from "lucide-react"

export default function Navigation() {
  const pathname = usePathname()

  const navItems = [
    {
      href: "/",
      label: "音檔轉錄",
      icon: <FileAudio className="w-4 h-4" />,
      description: "將音檔轉換為文字"
    },
    {
      href: "/video-converter",
      label: "影片轉音頻",
      icon: <FileVideo className="w-4 h-4" />,
      description: "從影片提取音頻"
    }
  ]

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg">
              <Home className="w-5 h-5" />
              音檔工具
            </Link>
            
            <div className="hidden md:flex items-center gap-2">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  <Button
                    variant={pathname === item.href ? "default" : "ghost"}
                    className="flex items-center gap-2"
                  >
                    {item.icon}
                    {item.label}
                  </Button>
                </Link>
              ))}
            </div>
          </div>
          
          <div className="md:hidden">
            <select
              value={pathname}
              onChange={(e) => window.location.href = e.target.value}
              className="px-3 py-2 border rounded-md bg-background"
            >
              {navItems.map((item) => (
                <option key={item.href} value={item.href}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="pb-4 text-center text-sm text-muted-foreground">
          {navItems.find(item => item.href === pathname)?.description || "音檔處理工具集"}
        </div>
      </div>
    </nav>
  )
} 