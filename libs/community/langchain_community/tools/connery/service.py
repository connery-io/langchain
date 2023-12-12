import json
from typing import List, Optional, Dict
from langchain_core.pydantic_v1 import BaseModel, root_validator
import requests
from langchain.utils.env import get_from_dict_or_env
from .models import Action
from .tool import ConneryAction

class ConneryService(BaseModel):
    """
    A service for interacting with the Connery Runner API.
    It gets the list of available actions from the Connery Runner, wraps them in ConneryAction Tools and returns them to the user.
    It also provides a method for running the actions.
    """

    runner_url: Optional[str] = None
    api_key: Optional[str] = None

    @root_validator()
    def validate_attributes(cls, values: Dict) -> Dict:
        """
        Validate the attributes of the ConneryService class.
        Parameters:
            values (dict): The arguments to validate.
        Returns:
            dict: The validated arguments.
        """

        runner_url = get_from_dict_or_env(values, "runner_url", "CONNERY_RUNNER_URL")
        api_key = get_from_dict_or_env(values, "api_key", "CONNERY_RUNNER_API_KEY")
        
        if not runner_url:
            raise ValueError("CONNERY_RUNNER_URL environment variable must be set.")
        if not api_key:
            raise ValueError("CONNERY_RUNNER_API_KEY environment variable must be set.")

        values['runner_url'] = runner_url
        values['api_key'] = api_key

        return values
    
    def list_actions(self) -> List[ConneryAction]:
        """
        Returns the list of actions available in the Connery Runner.
        Returns:
            List[ConneryAction]: The list of actions available in the Connery Runner.
        """

        return [ConneryAction.create_instance(action, self) for action in self._list_actions()]

    def get_action(self, action_id: str) -> ConneryAction:
        """
        Returns the specified action available in the Connery Runner.
        Parameters:
            action_id (str): The ID of the action to return.
        Returns:
            ConneryAction: The action with the specified ID.
        """

        return ConneryAction.create_instance(self._get_action(action_id), self)

    def run_action(self, action_id: str, input: Dict[str, str]) -> Dict[str, str]:
        """
        Runs the specified Connery Action with the provided input.
        Parameters:
            action_id (str): The ID of the action to run.
            input (Dict[str, str]): The input object expected by the action.
        Returns:
            Dict[str, str]: The output of the action.
        """

        return self._run_action(action_id, None, input)

    def _list_actions(self) -> List[Action]:
        """
        Returns the list of actions available in the Connery Runner.
        Returns:
            List[Action]: The list of actions available in the Connery Runner.
        """

        response = requests.get(
            f"{self.runner_url}/v1/actions",
            headers=self._get_headers()
        )

        if not response.ok:
            raise ValueError(f"Failed to list actions. Status code: {response.status_code}. Error message: {response.json()['error']['message']}")

        return [Action(**action) for action in response.json()['data']]

    def _get_action(self, action_id: str) -> Action:
        """
        Returns the specified action available in the Connery Runner.
        Parameters:
            action_id (str): The ID of the action to return.
        Returns:
            Action: The action with the specified ID.
        """

        actions = self._list_actions()
        action = next((action for action in actions if action.id == action_id), None)
        if not action:
            raise ValueError(f"The action with ID {action_id} was not found in the list of available actions in the Connery Runner.")
        return action

    def _run_action(self, action_id: str, prompt: str = None, input: Dict[str, str] = None) -> Dict[str, str]:
        """
        Runs the specified Connery Action with the provided input.
        Parameters:
            action_id (str): The ID of the action to run.
            prompt (str): This is a plain English prompt with all the information needed to run the action.
            input (Dict[str, str]): The input object expected by the action. If provided together with the prompt, the input takes precedence over the input specified in the prompt.
        Returns:
            Dict[str, str]: The output of the action.
        """

        response = requests.post(
            f"{self.runner_url}/v1/actions/{action_id}/run",
            headers=self._get_headers(),
            data=json.dumps({"prompt": prompt, "input": input})
        )

        if not response.ok:
            raise ValueError(f"Failed to run action. Status code: {response.status_code}. Error message: {response.json()['error']['message']}")

        if not response.json()['data']['output']:
            return {}
        else:
            return response.json()['data']['output']

    def _get_headers(self) -> Dict[str, str]:
        """
        Returns a standard set of HTTP headers to be used in API calls to the Connery runner.
        Returns:
            Dict[str, str]: The standard set of HTTP headers.
        """

        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
