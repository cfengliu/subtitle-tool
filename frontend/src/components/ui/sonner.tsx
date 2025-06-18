"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, ToasterProps, toast } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        style: {
          background: "hsl(0 0% 98%)",
          color: "hsl(222.2 84% 4.9%)",
          border: "1px solid hsl(214.3 31.8% 91.4%)",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
        },
        descriptionClassName:
        "!text-gray-900 dark:!text-gray-200 !opacity-100 font-medium",
      className: "border-l-4 border-l-blue-500",
      }}
      {...props}
    />
  )
}

export { Toaster, toast }
