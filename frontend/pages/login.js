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
  const { mutate: login, error } = useMutation(loginUser, {
    onSuccess: () => {
      // Once logged in, go to homepage
      router.push("/");
    },
  });

  const handleSubmit = () => {
    login({ email, password });
  };

  return (
    <Box maxW="md" mx="auto" mt="10">
      <FormControl>
        <FormLabel>Email</FormLabel>
        <Input value={email} onChange={(e) => setEmail(e.target.value)} />
      </FormControl>
      <FormControl mt={4}>
        <FormLabel>Password</FormLabel>
        <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </FormControl>
      {error && <Text color="red.400">Login failed. Check credentials.</Text>}
      <Button mt={4} colorScheme="blue" onClick={handleSubmit}>Login</Button>

      {/* NEW: Link to sign-up page */}
      <Box mt={4}>
        <Link as={NextLink} href="/signup" color="orange.300">
          Need an account? Sign up
        </Link>
      </Box>
    </Box>
  );
}
