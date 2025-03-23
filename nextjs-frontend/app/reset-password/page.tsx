import { ResetPasswordForm } from "@/components/reset-password-form"

export const metadata = {
  title: "Reset Password - Resume AI Assistant",
  description: "Set a new password for your Resume AI Assistant account",
}

export default function ResetPasswordPage() {
  return (
    <div className="container max-w-screen-md mx-auto py-16 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">Reset Password</h1>
      <ResetPasswordForm />
    </div>
  )
}