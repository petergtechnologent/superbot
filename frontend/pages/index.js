import { useState } from "react";
import { useMutation } from "react-query";
import { Box, Button, Textarea, Text, Spinner } from "@chakra-ui/react";
import { createConversation, generateCode, startDeployment } from "../utils/api";
import ActivityLog from "../components/ActivityLog";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [codeData, setCodeData] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [deploymentId, setDeploymentId] = useState(null);

  // 1. React Query mutation for creating a conversation
  const {
    mutate: doStartConversation,
    isLoading: isCreatingConversation,
  } = useMutation(createConversation, {
    onSuccess: (res) => {
      setConversationId(res.conversation_id);
      // Then automatically call generateCode
      doGenerateCode({ conversation_id: res.conversation_id, prompt });
    },
  });

  // 2. React Query mutation for generating code
  const {
    mutate: doGenerateCode,
    isLoading: isGeneratingCode,
  } = useMutation(generateCode, {
    onSuccess: (data) => {
      setCodeData(data.generated_code);
    },
  });

  // 3. React Query mutation for starting the orchestrator deployment
  const {
    mutate: doStartDeployment,
    isLoading: isStartingDeployment,
  } = useMutation(startDeployment, {
    onSuccess: (res) => {
      setDeploymentId(res.deployment_id);
    },
    onError: (err) => {
      console.error("Error starting deployment:", err);
      alert("Deployment failed to start. Check console for details.");
    },
  });

  // Called when user clicks "Generate"
  const handleSubmit = () => {
    // Reset old data
    setCodeData(null);
    setConversationId(null);
    setDeploymentId(null);

    // Start new conversation
    doStartConversation({ messages: [{ role: "user", content: prompt }] });
  };

  // Called when user clicks "Start Automated Deployment"
  const handleStartDeployment = () => {
    if (!conversationId || !codeData) {
      alert("Generate code first before deployment!");
      return;
    }
    doStartDeployment({
      conversation_id: conversationId,
      app_name: "my-app",
      max_iterations: 3,
    });
  };

  // You can show a loading spinner for any of these states
  const isLoadingAny = isCreatingConversation || isGeneratingCode || isStartingDeployment;

  return (
    <Box>
      {/* Prompt input */}
      <Textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe your app idea..."
      />
      <Button mt={4} onClick={handleSubmit} colorScheme="orange" disabled={isLoadingAny}>
        {isLoadingAny ? "Working..." : "Generate"}
      </Button>

      {/* Loading feedback if desired */}
      {isLoadingAny && (
        <Box mt={4}>
          <Spinner size="lg" color="orange.300" />
          <Text mt={2} color="orange.100">
            Please wait while we process your request...
          </Text>
        </Box>
      )}

      {/* Show generated code and deploy button */}
      {codeData && (
        <Box mt={4} p={4} bg="gray.700" color="white">
          <Text fontWeight="bold">Generated Code:</Text>
          <pre>{codeData}</pre>

          <Button mt={4} onClick={handleStartDeployment} colorScheme="teal" disabled={isStartingDeployment}>
            {isStartingDeployment ? "Deploying..." : "Start Automated Deployment"}
          </Button>
        </Box>
      )}

      {/* Real-time logs once deployment starts */}
      {deploymentId && (
        <Box mt={4}>
          <ActivityLog deploymentId={deploymentId} />
        </Box>
      )}
    </Box>
  );
}
