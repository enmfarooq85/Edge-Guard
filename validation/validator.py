import json
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ValidationError

class ValidationResult(BaseModel):
    is_valid: bool
    parsed_output: Optional[Dict[str, Any]] = None
    error_reason: Optional[str] = None

class OutputValidator:
    @staticmethod
    def validate_json_structure(output_text: str, required_keys: Optional[list] = None) -> ValidationResult:
        """Validates if output is valid JSON and contains required keys."""
        if not output_text or not output_text.strip():
            return ValidationResult(is_valid=False, error_reason="Output text is empty")

        try:
            # Attempt to parse JSON
            parsed = json.loads(output_text)
            if not isinstance(parsed, dict):
                return ValidationResult(is_valid=False, error_reason="Output is valid JSON but not a JSON Object (dict)")
            
            # Check for required schema keys if provided
            if required_keys:
                missing_keys = [k for k in required_keys if k not in parsed]
                if missing_keys:
                    return ValidationResult(
                        is_valid=False, 
                        parsed_output=parsed,
                        error_reason=f"Missing required schema keys: {missing_keys}"
                    )

            return ValidationResult(is_valid=True, parsed_output=parsed)

        except json.JSONDecodeError as e:
            return ValidationResult(is_valid=False, error_reason=f"JSON decode failure: {str(e)}")
        except Exception as e:
            return ValidationResult(is_valid=False, error_reason=f"Unexpected validation error: {str(e)}")

    @staticmethod
    def validate_pydantic_model(output_text: str, schema_class: type[BaseModel]) -> ValidationResult:
        """Validates JSON string against a strict Pydantic model class."""
        json_res = OutputValidator.validate_json_structure(output_text)
        if not json_res.is_valid or json_res.parsed_output is None:
            return json_res

        try:
            validated_obj = schema_class.model_validate(json_res.parsed_output)
            return ValidationResult(is_valid=True, parsed_output=validated_obj.model_dump())
        except ValidationError as e:
            return ValidationResult(is_valid=False, parsed_output=json_res.parsed_output, error_reason=f"Pydantic validation failed: {str(e)}")