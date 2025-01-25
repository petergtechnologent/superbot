import { useState } from "react";
import { useMutation } from "react-query";
import { Box, Button, Textarea, Text } from "@chakra-ui/react";
import { createConversation, generateCode } from "../utils/api";
import axios from "axios";
import ActivityLog from "../components/ActivityLog";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [codeData, setCodeData] = useState(null);
  const [deploymentId, setDeploymentId] = useState(null);

  // React Query mutation for generating code
  const { mutate: getCode } = useMutation(generateCode, {
    onSuccess: (data) => {
      setCodeData(data.generated_code);
    },
  });

  // React Query mutation for creating a conversation
  const { mutate: startConversation } = useMutation(createConversation, {
    onSuccess: (res) => {
      // Once conversation is created, automatically call generateCode
      getCode({ conversation_id: res.conversation_id, prompt });
    },
  });

  // Step 1: User enters prompt, we create a conversation and generate code
  const handleSubmit = () => {
    startConversation({ messages: [{ role: "user", content: prompt }] });
  };

  // Step 2: Once code is generated, user can start the automated deployment
  const handleStartDeployment = async () => {
    if (!codeData) {
      alert("Generate code first before deployment!");
      return;
    }

    // In reality, you’d use the real conversation_id returned from createConversation()
    // Below is a placeholder if you're not storing that ID yet
    const conversationId = "some-conversation-id";

    try {
      const res = await axios.post("http://localhost:8000/deployments/start", {
        conversation_id: conversationId,
        app_name: "my-app",
        max_iterations: 3,
      });
      setDeploymentId(res.data.deployment_id);
    } catch (err) {
      console.error("Error starting deployment:", err);
      alert("Deployment failed to start. Check console for details.");
    }
  };

  return (
    <Box>
      {/* Textarea for user’s prompt */}
      <Textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe your app idea..."
      />
      <Button mt={4} onClick={handleSubmit} colorScheme="orange">
        Generate
      </Button>

      {/* Display generated code */}
      {codeData && (
        <Box mt={4} p={4} bg="gray.700" color="white">
          <Text fontWeight="bold">Generated Code:</Text>
          <pre>{codeData}</pre>

          {/* Button to start the new orchestrator-based deployment */}
          <Button mt={4} onClick={handleStartDeployment} colorScheme="teal">
            Start Automated Deployment
          </Button>
        </Box>
      )}

      {/* Once deployment starts, show real-time logs */}
      {deploymentId && (
        <Box mt={4}>
          <ActivityLog deploymentId={deploymentId} />
        </Box>
      )}
    </Box>
  );
}
