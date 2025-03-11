"""
Trigger Agent Module

This module provides a specialized agent for triggering treatments based on specific customer criteria.
"""

import re
import logging
import json
import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

from src.agents.base_agent import BaseAgent
from src.utils.config import load_config
from src.tools.api_v2 import load_all_customer_data

# Load environment variables
load_dotenv()

class LiteLLMModel:
    """LLM wrapper for semantic analysis."""
    def __init__(self, model_id):
        self.model_id = model_id
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def completion(self, prompt):
        """
        Get completion from OpenAI API.
        
        Args:
            prompt: The prompt to send to the API
            
        Returns:
            API response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "You are a helpful AI analyzing customer interactions. Your task is to determine if a customer's interactions match a given description. Respond in valid JSON format only, without any markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Low temperature for more consistent analysis
            )
            # Get raw content and clean it up
            content = response.choices[0].message.content.strip()
            # Remove markdown code block if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if len(lines) > 2 else lines)
            if content.startswith("json"):
                content = content[4:].strip()
            
            # Parse the response content as JSON to validate it
            try:
                json.loads(content)  # Validate JSON
                return {"choices": [{"text": content}]}
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in OpenAI response: {str(e)}")
                logging.error(f"Raw content: {content}")
                return {"choices": [{"text": json.dumps({"matches": False, "reason": "Error parsing response"})}]}
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {str(e)}")
            raise

class TriggerAgent(BaseAgent):
    """
    Agent responsible for triggering treatments based on specific customer criteria.
    
    This agent analyzes customer data to identify those matching 
    particular conditions, such as having mentioned specific topics
    in their interactions, and allows triggering appropriate treatments.
    """
    
    def __init__(self, config=None):
        """
        Initialize the TriggerAgent.
        
        Args:
            config: Configuration object
        """
        super().__init__("Trigger", config)
        
        # Initialize configuration
        self.config = config
        
        # Initialize LLM
        model_id = config.model.get("id", "gpt-4") if hasattr(config, "model") else "gpt-4"
        self.llm = LiteLLMModel(model_id)
        
        # Setup predefined triggers
        self.predefined_triggers = {
            "network_issues": self._trigger_network_issues,
            "billing_disputes": self._trigger_billing_disputes,
            "churn_risk": self._trigger_churn_risk,
            "high_value": self._trigger_high_value,
            "roaming_issues": self._trigger_roaming_issues,
        }
        
        self.log("INFO", "TriggerAgent initialized")
    
    def process(self, message):
        """
        Process trigger requests.
        
        Args:
            message: Message containing the request details
            
        Returns:
            Triggering results
        """
        if isinstance(message, dict):
            message_type = message.get("type", "")
            
            if message_type == "trigger_customers":
                return self.trigger_customers(
                    message.get("customer_ids", []),
                    message.get("trigger_type", ""),
                    message.get("custom_trigger", {})
                )
            
            elif message_type == "list_triggers":
                return {
                    "status": "success",
                    "available_triggers": list(self.predefined_triggers.keys()) + ["custom"]
                }
            
            # For backward compatibility
            elif message_type == "filter_customers":
                self.log("WARNING", "Using deprecated 'filter_customers' message type. Use 'trigger_customers' instead.")
                return self.trigger_customers(
                    message.get("customer_ids", []),
                    message.get("filter_type", ""),
                    message.get("custom_filter", {})
                )
            
            else:
                self.log("WARNING", f"Unknown message type: {message_type}")
                return {"status": "error", "message": f"Unknown message type: {message_type}"}
        else:
            self.log("ERROR", f"Invalid message format: {type(message)}")
            return {"status": "error", "message": "Invalid message format"}
    
    def trigger_customers(self, customer_ids, trigger_type, custom_trigger=None):
        """
        Trigger customers based on specified criteria.
        
        Args:
            customer_ids: List of customer IDs to analyze
            trigger_type: Type of trigger to apply ('network_issues', 'billing_disputes', etc.)
            custom_trigger: Custom trigger description or parameters
            
        Returns:
            List of matching customer IDs and reasons
        """
        self.log("INFO", f"Triggering analysis for {len(customer_ids)} customers using '{trigger_type}' criteria")
        
        if not customer_ids:
            return {
                "status": "error",
                "message": "No customer IDs provided"
            }
        
        # Load customer data
        try:
            all_customer_data = load_all_customer_data(customer_ids)
        except Exception as e:
            self.log("ERROR", f"Failed to load customer data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to load customer data: {str(e)}"
            }
        
        # Apply trigger
        if trigger_type in self.predefined_triggers:
            # Use predefined trigger
            trigger_func = self.predefined_triggers[trigger_type]
            matches = []
            
            for customer_id in customer_ids:
                customer_data = all_customer_data.get(customer_id, {})
                if not customer_data:
                    continue
                
                # Apply the trigger and get reason if it matches
                match_reason = trigger_func(customer_data)
                if match_reason:
                    matches.append({
                        "customer_id": customer_id,
                        "reason": match_reason
                    })
            
            return {
                "status": "success",
                "matches": matches,
                "total_matches": len(matches),
                "trigger_applied": trigger_type
            }
            
        elif trigger_type == "custom":
            if not custom_trigger or not isinstance(custom_trigger, (str, dict)):
                return {
                    "status": "error",
                    "message": "Invalid custom trigger format"
                }

            # If custom_trigger is a string, use it as the semantic trigger description
            trigger_description = custom_trigger if isinstance(custom_trigger, str) else custom_trigger.get("description")
            if not trigger_description:
                return {
                    "status": "error",
                    "message": "No trigger description provided"
                }

            matches = []
            for customer_id in customer_ids:
                customer_data = all_customer_data.get(customer_id, {})
                if not customer_data:
                    continue

                # Analyze customer interactions using LLM
                match_result = self._analyze_with_llm(customer_data, trigger_description)
                if match_result.get("matches"):
                    matches.append({
                        "customer_id": customer_id,
                        "reason": match_result.get("reason"),
                        "evidence": match_result.get("evidence", [])
                    })

            return {
                "status": "success",
                "matches": matches,
                "total_matches": len(matches),
                "trigger_applied": "custom",
                "trigger_description": trigger_description
            }
        else:
            return {
                "status": "error",
                "message": f"Unknown trigger type: {trigger_type}"
            }
    
    def _analyze_with_llm(self, customer_data: Dict[str, Any], trigger_description: str) -> Dict[str, Any]:
        """
        Analyze customer data using LLM to determine if they match the trigger description.
        
        Args:
            customer_data: Customer data including interactions
            trigger_description: Description of what to look for
            
        Returns:
            Dict containing match results and evidence
        """
        # Prepare relevant customer interactions
        interactions = []
        
        # Add call transcripts
        for call in customer_data.get("call_transcripts", []):
            interactions.append({
                "type": "call",
                "date": call.get("date"),
                "content": call.get("summary"),
                "sentiment": call.get("sentiment")
            })
            
        # Add web chat transcripts
        for chat in customer_data.get("web_transcripts", []):
            interactions.append({
                "type": "chat",
                "date": chat.get("date"),
                "content": chat.get("summary"),
                "sentiment": chat.get("sentiment")
            })

        if not interactions:
            return {"matches": False}

        # Prepare the prompt for the LLM
        prompt = f"""Analyze these customer interactions and determine if they match the following description:
"{trigger_description}"

Customer Interactions:
{json.dumps(interactions, indent=2)}

Answer in JSON format:
{{
    "matches": true/false,
    "reason": "Brief explanation of why this customer matches or doesn't match",
    "evidence": ["List of relevant quotes or summaries from interactions"]
}}"""

        try:
            # Get LLM response
            response = self.llm.completion(prompt)
            result = json.loads(response["choices"][0]["text"])
            return result
        except Exception as e:
            self.log("ERROR", f"Error in LLM analysis: {str(e)}")
            return {"matches": False}
    
    def _trigger_network_issues(self, customer_data):
        """Trigger for customers with network-related issues."""
        # Look in call transcripts
        if "call_transcripts" in customer_data:
            for call in customer_data["call_transcripts"]:
                summary = call.get("summary", "").lower()
                if any(term in summary for term in ["network", "connection", "signal", "drops", "quality", "speed"]):
                    if "network issues" in summary or "connection issues" in summary:
                        return f"Call transcript mentions network issues: '{self._get_snippet(summary, 'network')}'"
        
        # Look in web transcripts
        if "web_transcripts" in customer_data:
            for web in customer_data["web_transcripts"]:
                summary = web.get("summary", "").lower()
                if any(term in summary for term in ["network", "connection", "signal", "drops", "quality", "speed"]):
                    if "network issues" in summary or "connection issues" in summary:
                        return f"Web chat mentions network issues: '{self._get_snippet(summary, 'network')}'"
        
        # Look in network data
        if "network_data" in customer_data:
            for data in customer_data["network_data"]:
                if data.get("connection_quality") == "poor":
                    return f"Poor network connection quality detected: {data.get('download_speed_mbps')}Mbps down, {data.get('latency_ms')}ms latency"
                
                # Check for high latency or packet loss
                if data.get("latency_ms", 0) > 70 or data.get("packet_loss_percent", 0) > 1.5:
                    return f"Network metrics indicate potential issues: {data.get('latency_ms')}ms latency, {data.get('packet_loss_percent')}% packet loss"
        
        return None
    
    def _trigger_billing_disputes(self, customer_data):
        """Trigger for customers with billing disputes."""
        # Look in call transcripts
        if "call_transcripts" in customer_data:
            for call in customer_data["call_transcripts"]:
                summary = call.get("summary", "").lower()
                if any(term in summary for term in ["bill", "charge", "overcharge", "payment", "dispute"]):
                    if "billing dispute" in summary or "unexpected charge" in summary:
                        return f"Call transcript mentions billing dispute: '{self._get_snippet(summary, 'bill')}'"
        
        # Check for overdue payments
        if "billing_data" in customer_data:
            for bill in customer_data["billing_data"]:
                if bill.get("payment_status") == "overdue":
                    return f"Overdue payment detected: {bill.get('monthly_charge')} + {bill.get('additional_charges')} charges"
                    
                if float(bill.get("additional_charges", 0)) > 20:
                    return f"High additional charges: {bill.get('additional_charges')}"
        
        return None
    
    def _trigger_churn_risk(self, customer_data):
        """Trigger for customers with high churn risk."""
        # Check churn score data
        if "churn_score" in customer_data:
            for score in customer_data["churn_score"]:
                if score.get("churn_probability", 0) > 0.5:
                    return f"High churn probability: {score.get('churn_probability')}, Risk factors: {', '.join(score.get('risk_factors', []))}"
        
        # Check for negative sentiment calls
        if "call_transcripts" in customer_data:
            negative_calls = [c for c in customer_data["call_transcripts"] if c.get("sentiment") == "negative"]
            if len(negative_calls) >= 2:
                return f"Multiple negative sentiment calls detected ({len(negative_calls)})"
        
        return None
    
    def _trigger_high_value(self, customer_data):
        """Trigger for high-value customers."""
        # Check usage data for high usage
        if "usage_data" in customer_data:
            for usage in customer_data["usage_data"]:
                if float(usage.get("data_usage_gb", 0)) > 30:
                    return f"High data usage: {usage.get('data_usage_gb')}GB"
        
        # Check billing data for high monthly charge
        if "billing_data" in customer_data:
            for bill in customer_data["billing_data"]:
                if float(bill.get("monthly_charge", 0)) > 80:
                    return f"High monthly charge: £{bill.get('monthly_charge')}"
        
        # Check customer lifetime
        if "churn_score" in customer_data:
            for score in customer_data["churn_score"]:
                if score.get("customer_lifetime_months", 0) > 36:
                    return f"Long-term customer: {score.get('customer_lifetime_months')} months"
        
        return None
    
    def _trigger_roaming_issues(self, customer_data):
        """Trigger for customers with roaming-related issues."""
        # Look in call transcripts
        if "call_transcripts" in customer_data:
            for call in customer_data["call_transcripts"]:
                summary = call.get("summary", "").lower()
                if any(term in summary for term in ["roaming", "international", "abroad", "travel"]):
                    return f"Call transcript mentions roaming issues: '{self._get_snippet(summary, 'roaming')}'"
        
        # Check for roaming data usage
        if "usage_data" in customer_data:
            for usage in customer_data["usage_data"]:
                if float(usage.get("roaming_data_gb", 0)) > 0:
                    return f"Recent roaming data usage: {usage.get('roaming_data_gb')}GB"
        
        return None
    
    def _get_snippet(self, text, keyword, context_chars=40):
        """Get a snippet of text surrounding a keyword."""
        if not text or not keyword:
            return ""
            
        text = text.lower()
        keyword = keyword.lower()
        
        # Find keyword position
        pos = text.find(keyword)
        if pos == -1:
            return ""
            
        # Get surrounding context
        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(keyword) + context_chars)
        
        # Add ellipsis if needed
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        
        return f"{prefix}{text[start:end]}{suffix}" 