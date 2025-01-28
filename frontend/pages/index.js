// File: frontend/pages/index.js
import { useState } from "react";
import { useMutation } from "react-query";
import Head from "next/head";
import {
  Box,
  Button,
  Textarea,
  Text,
  Input,
  Flex,
  Spinner,
  Checkbox,
  Heading,
  useToast,
} from "@chakra-ui/react";
import {
  transformFlexSpec,
  createConversation,
  generateCode,
  startDeployment,
} from "../utils/api";
import ActivityLog from "../components/ActivityLog";

export default function Home() {
  const toast = useToast();
  const [userIdea, setUserIdea] = useState("");
  const [flexPort, setFlexPort] = useState("9000");
  const [maxIterations, setMaxIterations] = useState(5);
  const [troubleMode, setTroubleMode] = useState(false);

  const [conversationId, setConversationId] = useState(null);
  const [deploymentId, setDeploymentId] = useState(null);
  const [codeData, setCodeData] = useState(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

  // 1) Transform user input => Flex Spec
  const { mutate: doTransformSpec, isLoading: isTransformLoading } = useMutation(
    transformFlexSpec,
    {
      onSuccess: (spec) => {
        // 2) Create a conversation with that spec
        const specMessage = {
          role: "user",
          content: JSON.stringify(spec, null, 2),
        };
        doCreateConversation({ messages: [specMessage] });
      },
      onError: () => {
        setIsGenerating(false);
        toast({
          title: "Error",
          description: "Error converting input into a Flex Spec!",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      },
    }
  );

  // 2) Create conversation => on success => generate code
  const { mutate: doCreateConversation } = useMutation(createConversation, {
    onSuccess: (res) => {
      setConversationId(res.conversation_id);
      doGenerateCode({
        conversation_id: res.conversation_id,
        prompt: "Generate code for the above Flex Spec.",
      });
    },
    onError: () => {
      setIsGenerating(false);
      toast({
        title: "Error",
        description: "Error creating conversation!",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    },
  });

  // 3) Generate code
  const { mutate: doGenerateCode } = useMutation(generateCode, {
    onSuccess: (data) => {
      setCodeData(data.generated_code);
      setIsGenerating(false);
    },
    onError: () => {
      setIsGenerating(false);
      toast({
        title: "Error",
        description: "Error generating code!",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    },
  });

  // 4) Start deployment
  const { mutate: doStartDeploy } = useMutation(startDeployment, {
    onSuccess: (res) => {
      setDeploymentId(res.deployment_id);
      setIsDeploying(false);
    },
    onError: () => {
      setIsDeploying(false);
      toast({
        title: "Error",
        description: "Error starting deployment!",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    },
  });

  const handleSubmitPrompt = () => {
    setIsGenerating(true);
    setCodeData(null);
    setDeploymentId(null);
    setConversationId(null);

    doTransformSpec({ userIdea });
  };

  const handleStartDeployment = () => {
    if (!conversationId) {
      toast({
        title: "No conversation",
        description: "Please generate code before deploying.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    setIsDeploying(true);

    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const uniqueAppName = `flex-fastapi-app-${randomSuffix}`;

    doStartDeploy({
      conversation_id: conversationId,
      app_name: uniqueAppName,
      max_iterations: maxIterations,
      port_number: parseInt(flexPort, 10) || 9000,
      trouble_mode: troubleMode,
    });
  };

  return (
    <Box p={4}>
      <Head>
        <title>Fast Service Generator</title>
      </Head>

      <Heading mb={4}>Fast Service Generator</Heading>

      <Text fontSize="md" mb={2}>
        Enter your microservice need:
      </Text>
      <Textarea
        value={userIdea}
        onChange={(e) => setUserIdea(e.target.value)}
        placeholder="e.g., 'A service on port 9090 with a GET /random endpoint...'"
        mb={4}
      />

      <Flex align="center" mb={4}>
        <Text mr={2}>Port Number:</Text>
        <Input
          type="number"
          width="100px"
          value={flexPort}
          onChange={(e) => setFlexPort(e.target.value)}
        />
      </Flex>

      <Flex align="center" mb={4}>
        <Text mr={2}>Max Iterations:</Text>
        <Input
          type="number"
          width="100px"
          value={maxIterations}
          onChange={(e) => setMaxIterations(e.target.value)}
        />
      </Flex>

      <Checkbox
        isChecked={troubleMode}
        onChange={(e) => setTroubleMode(e.target.checked)}
        mb={4}
      >
        Trouble Mode (Leave Container Running on Failure)
      </Checkbox>

      <Button
        onClick={handleSubmitPrompt}
        colorScheme="blue"
        isLoading={isTransformLoading || isGenerating}
        mb={6}
      >
        Generate Code
      </Button>

      {isGenerating && (
        <Flex mt={2} align="center">
          <Spinner mr={2} />
          <Text>Generating code, please wait...</Text>
        </Flex>
      )}

      {/* SERVICE SPEC (Multi-file display) */}
      {codeData && (
        <Box mt={4}>
          <GeneratedFilesDisplay codeData={codeData} />
          <Button
            mt={4}
            onClick={handleStartDeployment}
            colorScheme="orange"
            isLoading={isDeploying}
          >
            Start Automated Deployment
          </Button>
        </Box>
      )}

      {isDeploying && (
        <Flex mt={2} align="center">
          <Spinner mr={2} />
          <Text>Deploying...</Text>
        </Flex>
      )}

      {deploymentId && (
        <Box mt={4}>
          <ActivityLog deploymentId={deploymentId} />
        </Box>
      )}
    </Box>
  );
}

// Helper component for file display
function GeneratedFilesDisplay({ codeData }) {
  const [parsed, setParsed] = useState(null);

  if (parsed === null) {
    try {
      setParsed(JSON.parse(codeData));
    } catch (err) {
      setParsed(false);
    }
  }

  if (parsed === false) {
    return (
      <Box p={4} bg="gray.700" color="white">
        <Text fontWeight="bold" mb={2}>
          Service Spec (Raw):
        </Text>
        <pre>{codeData}</pre>
      </Box>
    );
  }

  if (parsed && typeof parsed === "object") {
    return (
      <Box>
        <Text fontWeight="bold" mb={2}>
          Generated Files:
        </Text>
        {Object.entries(parsed).map(([filename, content]) => (
          <Box
            key={filename}
            mt={3}
            p={3}
            bg="gray.700"
            borderRadius="md"
            color="white"
          >
            <Text fontWeight="semibold" mb={1}>
              {filename}
            </Text>
            <Box
              bg="gray.900"
              p={2}
              borderRadius="md"
              maxH="300px"
              overflowY="auto"
            >
              <pre style={{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}>
                {content}
              </pre>
            </Box>
          </Box>
        ))}
      </Box>
    );
  }

  return null;
}
