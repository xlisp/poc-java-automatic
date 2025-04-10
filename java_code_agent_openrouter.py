import autogen
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import os
import json
import requests

# OpenRouter API configuration
OPENROUTER_API_KEY = os.environ['OPENROUTER_API_KEY']

class OpenRouterLLM:
    def __init__(self, model="anthropic/claude-3.5-sonnet"):
        self.model = model
        
    def create_completion(self, messages):
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}"
            },
            data=json.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.7,
            })
        )
        return response.json()

class JavaProjectManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src" / "main" / "java"
        self.test_dir = self.project_root / "src" / "test" / "java"
        self.pom_path = self.project_root / "pom.xml"

    def update_pom_dependencies(self, dependencies):
        """Update pom.xml with new dependencies"""
        if not self.pom_path.exists():
            raise FileNotFoundError("pom.xml not found in the project root")

        tree = ET.parse(self.pom_path)
        root = tree.getroot()
        
        # Find or create dependencies section
        deps = root.find("{http://maven.apache.org/POM/4.0.0}dependencies")
        if deps is None:
            deps = ET.SubElement(root, "dependencies")

        # Add new dependencies
        for dep in dependencies:
            new_dep = ET.SubElement(deps, "dependency")
            ET.SubElement(new_dep, "groupId").text = dep["groupId"]
            ET.SubElement(new_dep, "artifactId").text = dep["artifactId"]
            ET.SubElement(new_dep, "version").text = dep["version"]

        tree.write(self.pom_path, encoding="utf-8", xml_declaration=True)

    def compile_project(self):
        """Compile the Java project using Maven"""
        try:
            result = subprocess.run(
                ["mvn", "compile"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout
        except Exception as e:
            return False, str(e)

    def run_tests(self):
        """Run project tests using Maven"""
        try:
            result = subprocess.run(
                ["mvn", "test"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stdout
        except Exception as e:
            return False, str(e)

# Configure custom LLM config for OpenRouter
llm_config = {
    "config_list": [{
        "model": "anthropic/claude-3.5-sonnet",
        "api_key": OPENROUTER_API_KEY,
        "base_url": "https://openrouter.ai/api/v1/chat/completions"
    }],
    "temperature": 0.7,
    "timeout": 120,
    "cache_seed": 42
}

# Create the assistant agent for Java code generation
java_assistant = autogen.AssistantAgent(
    name="java_coder",
    llm_config=llm_config,
    system_message="""You are an expert Java developer. You write clean, well-documented,
    and efficient Java code. You also write comprehensive unit tests using JUnit 5.
    Always follow best practices and design patterns."""
)

# Create the user proxy agent with OpenRouter configuration
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    code_execution_config={
        "work_dir": "coding_workspace",
        "use_docker": False  # Set to True if you want to use Docker for code execution
    },
    llm_config=llm_config
)

# Create project manager instance
project_manager = JavaProjectManager("./")

def main():
    # Example conversation to generate Java code and tests
    user_proxy.initiate_chat(
        java_assistant,
        message="""Please create a simple Java class called Calculator with basic arithmetic 
        operations and corresponding unit tests."""
    )

    # Example dependencies to add to pom.xml
    dependencies = [
        {
            "groupId": "org.junit.jupiter",
            "artifactId": "junit-jupiter-api",
            "version": "5.9.2"
        },
        {
            "groupId": "org.junit.jupiter",
            "artifactId": "junit-jupiter-engine",
            "version": "5.9.2"
        },
        {
            "groupId": "org.junit.jupiter",
            "artifactId": "junit-jupiter-params",
            "version": "5.9.2"
        }
    ]

    # Update pom.xml with required dependencies
    try:
        project_manager.update_pom_dependencies(dependencies)
        print("Successfully updated pom.xml with dependencies")
    except Exception as e:
        print(f"Error updating pom.xml: {e}")

    # Compile the project
    success, output = project_manager.compile_project()
    if success:
        print("Project compiled successfully")
    else:
        print(f"Compilation failed: {output}")

    # Run tests
    success, output = project_manager.run_tests()
    if success:
        print("All tests passed successfully")
    else:
        print(f"Tests failed: {output}")

if __name__ == "__main__":
    main()
