import { ForgotPasswordForm } from "@/components/forgot-password-form"

export const metadata = {
  title: "Forgot Password - Resume AI Assistant",
  description: "Reset your Resume AI Assistant password",
}

export default function ForgotPasswordPage() {
  return (
    <div className="container max-w-screen-md mx-auto py-16 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">Forgot Password</h1>
      <ForgotPasswordForm />
    </div>
  )
}