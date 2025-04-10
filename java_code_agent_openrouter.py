import autogen
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import os
import json
import requests
from datetime import datetime
import logging

# Configuration constants
CURRENT_UTC = "2025-04-10 06:41:25"
CURRENT_USER = "xlisp"
OPENROUTER_API_KEY = os.environ['OPENROUTER_API_KEY']

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OpenRouterConfig:
    """Configuration for OpenRouter API calls"""
    api_base = "https://openrouter.ai/api/v1"
    
    @staticmethod
    def get_headers():
        return {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Java Code Generator",
            "User-Agent": f"JavaCodeGenerator/{CURRENT_USER}"
        }

class JavaProjectManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.src_dir = self.project_root / "src" / "main" / "java"
        self.test_dir = self.project_root / "src" / "test" / "java"
        self.pom_path = self.project_root / "pom.xml"
        
        # Create directories if they don't exist
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)

    def update_pom_dependencies(self, dependencies):
        """Update pom.xml with new dependencies"""
        if not self.pom_path.exists():
            self._create_default_pom()
            self.logger.info(f"Created new pom.xml at {self.pom_path}")

        try:
            tree = ET.parse(self.pom_path)
            root = tree.getroot()
            
            deps = root.find("{http://maven.apache.org/POM/4.0.0}dependencies")
            if deps is None:
                deps = ET.SubElement(root, "dependencies")

            for dep in dependencies:
                new_dep = ET.SubElement(deps, "dependency")
                ET.SubElement(new_dep, "groupId").text = dep["groupId"]
                ET.SubElement(new_dep, "artifactId").text = dep["artifactId"]
                ET.SubElement(new_dep, "version").text = dep["version"]

            tree.write(self.pom_path, encoding="utf-8", xml_declaration=True)
            self.logger.info("Successfully updated dependencies in pom.xml")
            
        except Exception as e:
            self.logger.error(f"Error updating pom.xml: {str(e)}")
            raise

    def _create_default_pom(self):
        """Create a default pom.xml file"""
        pom_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>java-autogen-project</artifactId>
    <version>1.0-SNAPSHOT</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <junit.jupiter.version>5.9.2</junit.jupiter.version>
        <project.created.by>{CURRENT_USER}</project.created.by>
        <project.created.date>{CURRENT_UTC}</project.created.date>
    </properties>

    <dependencies>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.0.0</version>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.10.1</version>
                <configuration>
                    <source>${{maven.compiler.source}}</source>
                    <target>${{maven.compiler.target}}</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""
        with open(self.pom_path, 'w') as f:
            f.write(pom_content)

    def compile_project(self):
        """Compile the Java project using Maven"""
        try:
            self.logger.info("Starting project compilation...")
            result = subprocess.run(
                ["mvn", "compile"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("Project compilation successful")
            else:
                self.logger.error(f"Compilation failed: {result.stderr}")
            return result.returncode == 0, result.stdout
        except Exception as e:
            self.logger.error(f"Error during compilation: {str(e)}")
            return False, str(e)

    def run_tests(self):
        """Run project tests using Maven"""
        try:
            self.logger.info("Starting test execution...")
            result = subprocess.run(
                ["mvn", "test"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("Tests executed successfully")
            else:
                self.logger.error(f"Test execution failed: {result.stderr}")
            return result.returncode == 0, result.stdout
        except Exception as e:
            self.logger.error(f"Error during test execution: {str(e)}")
            return False, str(e)

    def save_java_file(self, filename: str, content: str, is_test: bool = False):
        """Save a Java file to the appropriate directory"""
        try:
            target_dir = self.test_dir if is_test else self.src_dir
            file_path = target_dir / filename
            
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add file header with metadata
            header = f"""/*
 * Generated by JavaCodeGenerator
 * Created by: {CURRENT_USER}
 * Created at: {CURRENT_UTC}
 */

"""
            content = header + content
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Successfully saved file: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error saving file {filename}: {str(e)}")
            raise

class CustomAssistantAgent(autogen.AssistantAgent):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.logger = logging.getLogger(__name__)
        
    def generate_reply(self, messages, sender, config=None):
        """Generate reply using OpenRouter API"""
        try:
            # Convert messages to the format expected by OpenRouter
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict) and 'content' in msg:
                    formatted_messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg['content']
                    })
                elif isinstance(msg, str):
                    formatted_messages.append({
                        'role': 'user',
                        'content': msg
                    })

            # Add context about current user and time
            context_message = {
                'role': 'system',
                'content': f"Current context - User: {CURRENT_USER}, DateTime: {CURRENT_UTC}"
            }
            formatted_messages.insert(0, context_message)

            response = requests.post(
                f"{OpenRouterConfig.api_base}/chat/completions",
                headers=OpenRouterConfig.get_headers(),
                json={
                    "model": "anthropic/claude-3-sonnet",
                    "messages": formatted_messages,
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            )
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise Exception("No valid response received from OpenRouter API")
                
        except Exception as e:
            self.logger.error(f"Error generating reply: {str(e)}")
            return "I apologize, but I encountered an error while processing your request. Please try again."

def main():
    try:
        logger.info(f"Starting Java code generation session - User: {CURRENT_USER}, Time: {CURRENT_UTC}")
        
        # Initialize project manager
        project_root = Path("./java_project")
        project_manager = JavaProjectManager(project_root)
        
        # Create the assistant agent
        java_assistant = CustomAssistantAgent(
            name="java_coder",
            system_message=f"""You are an expert Java developer. Current context:
            - User: {CURRENT_USER}
            - DateTime: {CURRENT_UTC}
            
            Write clean, well-documented, and efficient Java code.
            Generate comprehensive unit tests using JUnit 5.
            Follow best practices and design patterns.
            Include proper documentation and timestamps in generated code.""",
            llm_config={
                "temperature": 0.7,
                "timeout": 120
            }
        )

        # Create the user proxy agent
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="TERMINATE",
            max_consecutive_auto_reply=10,
            code_execution_config={
                "work_dir": str(project_root),
                "use_docker": False
            }
        )

        # Add JUnit dependencies
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

        # Update pom.xml with dependencies
        project_manager.update_pom_dependencies(dependencies)
        logger.info("Successfully updated pom.xml with dependencies")

        # Start the conversation to generate code
        user_proxy.initiate_chat(
            java_assistant,
            message="""Please create a Java Calculator class with methods for addition, 
            subtraction, multiplication, and division. Include comprehensive unit tests."""
        )

        # Compile and test the project
        compile_success, compile_output = project_manager.compile_project()
        if compile_success:
            logger.info("Project compiled successfully")
            
            test_success, test_output = project_manager.run_tests()
            if test_success:
                logger.info("All tests passed successfully")
            else:
                logger.error(f"Tests failed: {test_output}")
        else:
            logger.error(f"Compilation failed: {compile_output}")

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()

