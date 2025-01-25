import { useState } from "react";
import { useMutation } from "react-query";
import { Box, Button, Textarea } from "@chakra-ui/react";
import { createConversation, generateCode } from "../utils/api";

export default function Home() {
  const [prompt, setPrompt] = useState("");

  const { mutate: getCode, data: codeData } = useMutation(generateCode);

  const { mutate: startConversation } = useMutation(createConversation, {
    onSuccess: (res) => {
      // Once conversation is created, automatically call generateCode
      getCode({ conversation_id: res.conversation_id, prompt });
    },
  });

  const handleSubmit = () => {
    startConversation({ messages: [{ role: "user", content: prompt }] });
  };

  return (
    <Box>
      <Textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe your app idea..."
      />
      <Button mt={4} onClick={handleSubmit} colorScheme="orange">
        Generate
      </Button>

      {codeData && (
        <Box mt={4} p={4} bg="gray.700" color="white">
          <pre>{codeData.generated_code}</pre>
        </Box>
      )}
    </Box>
  );
}
