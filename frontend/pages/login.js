// File: frontend/pages/login.js
import { useState } from "react";
import { useRouter } from "next/router";
import { Box, Button, Input, FormControl, FormLabel, Text, Link } from "@chakra-ui/react";
import { useMutation } from "react-query";
import NextLink from "next/link";
import { loginUser } from "../utils/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  // We define a mutation with the `loginUser` function from our `api.js`.
  const { mutate: doLogin, error, isError, isLoading } = useMutation(loginUser, {
    onSuccess: (data) => {
      // data.access_token is returned from backend
      // Store it in localStorage so we can pass it in future requests
      localStorage.setItem("access_token", data.access_token);
      router.push("/"); // or any route
    },
    onError: (err) => {
      console.error("Login error:", err);
    },
  });

  const handleSubmit = () => {
    doLogin({ email, password });
  };

  return (
    <Box maxW="md" mx="auto" mt="10">
      <FormControl mb={4}>
        <FormLabel>Email</FormLabel>
        <Input
          type="email"
          placeholder="Enter email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </FormControl>

      <FormControl mb={4}>
        <FormLabel>Password</FormLabel>
        <Input
          type="password"
          placeholder="Enter password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </FormControl>

      {isError && <Text color="red.400">Login failed. Check credentials.</Text>}

      <Button
        colorScheme="blue"
        onClick={handleSubmit}
        isLoading={isLoading}
        disabled={isLoading}
      >
        Login
      </Button>

      <Box mt={4}>
        <Link as={NextLink} href="/signup">
          Need an account? Sign up
        </Link>
      </Box>
    </Box>
  );
}
