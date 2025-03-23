import { RegisterForm } from "@/components/register-form"

export const metadata = {
  title: "Create Account - Resume AI Assistant",
  description: "Create a new account for Resume AI Assistant",
}

export default function RegisterPage() {
  return (
    <div className="container max-w-screen-md mx-auto py-16 px-4">
      <h1 className="text-3xl font-bold text-center mb-8">Create Account</h1>
      <RegisterForm />
    </div>
  )
}