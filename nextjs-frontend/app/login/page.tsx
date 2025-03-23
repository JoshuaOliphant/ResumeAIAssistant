import { LoginForm } from "@/components/login-form"

export const metadata = {
  title: "Sign In - Resume AI Assistant",
  description: "Sign in to your Resume AI Assistant account",
}

export default function LoginPage() {
  return (
    <div className="container max-w-screen-md mx-auto py-16 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">Sign In</h1>
      <LoginForm />
    </div>
  )
}