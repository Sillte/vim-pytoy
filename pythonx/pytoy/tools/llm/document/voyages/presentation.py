import logging
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.shared.timertask import add_log_message
from pytoy.tools.llm.pytoy_fairy import PytoyFairy, FairyKernel
from pytoy.tools.llm.document.voyages.domain import Compass, EvolvePolicy, Bearing, CompassAlignment, VoyageState
from pytoy.tools.llm.document.voyages.application import EvolveRequest, EvolveResponse, ReflectRequest, ReflectResponse, VoyageInteractionCreator
from pytoy.tools.llm.utils import TomlConverter
from pytoy.shared.ui.notifications import EphemeralNotification
from typing import Mapping, Any


class DocumentVoyageUI:
    def __init__(self, pytoy_fairy: PytoyFairy,
                       directive_buffer_name: str = "voyage", 
                      ):
        self._pytoy_fairy = pytoy_fairy
        self._interaction_creator = VoyageInteractionCreator(self._pytoy_fairy.kernel)
        self._directive_buffer_name = directive_buffer_name
        self._toml_converter = TomlConverter()
        self._toml_class_map = VoyageState.schema_map()
        
    @property
    def logger(self) -> logging.Logger:
        return self._pytoy_fairy.llm_context.logger

        
    @property
    def pytoy_fairy(self) -> PytoyFairy:
        return self._pytoy_fairy
    
    @property
    def manuscript(self) -> str:
        """Get the manuscript.
        """
        return self.pytoy_fairy.buffer.content

    def _complete_states(self) -> VoyageState:
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        toml_text = directive_buffer.content
        initial_state = VoyageState.initial()
        try:
            basemodels = self._toml_converter.to_basemodels(toml_text, self._toml_class_map)
            state = initial_state.model_copy(update=basemodels)
        except (ValueError):
            state = initial_state
        return state
    
    def check_state(self) -> None:
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        toml_text = directive_buffer.content
        try:
            basemodels = self._toml_converter.to_basemodels(toml_text, self._toml_class_map)
        except ValueError as e:
            EphemeralNotification().notify("Not valid `State`. See `Log`.")
            self.logger.info(str(e))
        try:
            VoyageState.model_validate(basemodels)
        except Exception as e:
            self.logger.info(str(e))
            EphemeralNotification().notify("Not valid `VoyageState`. See `Log`.")
        else:
            EphemeralNotification().notify("OK. valid `VoyageState`.")
    
    def on_failure(self, exception: Exception):
        self.pytoy_fairy.llm_context.logger.info(f"Exception:{exception}")
        add_log_message(str(exception))
        EphemeralNotification().notify("Error happens. See `log` or `:messages`.")
    
    def on_evolve(self, evolve_response: EvolveResponse) -> None:
        self.pytoy_fairy.llm_context.logger.info(f"EvolveResponse:{evolve_response}")
        state = self._complete_states()
        new_state = state.model_copy(update={"compass": evolve_response.compass})
        basemodels = new_state.to_basemodels()
        directive_content = self._toml_converter.from_basemodels(basemodels)
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        directive_buffer.init_buffer(directive_content)
        self.pytoy_fairy.buffer.init_buffer(evolve_response.manuscript)

    
    def _construct_evolve_request(self) -> EvolveRequest:
        state = self._complete_states()
        manuscript = self.pytoy_fairy.buffer.content
        evolve_request = EvolveRequest(compass=state.compass, evolve_policy=state.evolve_policy, manuscript=manuscript)
        self.pytoy_fairy.llm_context.logger.info("EvolveRequest:" +  str(evolve_request))
        return evolve_request

    
    def _construct_reflect_request(self) -> ReflectRequest:
        state = self._complete_states()
        manuscript = self.pytoy_fairy.buffer.content
        reflect_request= ReflectRequest(manuscript=manuscript, compass=state.compass)
        self.pytoy_fairy.llm_context.logger.info("ReflectRequest:" +  str(reflect_request))
        return reflect_request

    def on_reflect(self, reflect_response: ReflectResponse) -> None:
        self.pytoy_fairy.llm_context.logger.info(f"ReflectResponse:{reflect_response}")
        state = self._complete_states()

        new_state = state.model_copy(update={"compass": reflect_response.compass, "bearing": reflect_response.bearing})
        basemodels = new_state.to_basemodels()
        directive_content = self._toml_converter.from_basemodels(basemodels)
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        directive_buffer.init_buffer(directive_content)
    
    def evolve(self):
        evolve_request = self._construct_evolve_request()
        self._interaction_creator.create_evolve_interaction(evolve_request, on_success=self.on_evolve, on_failure=self.on_failure)

    def reflect(self):
        reflect_request = self._construct_reflect_request()
        self._interaction_creator.create_reflect_interaction(reflect_request, on_success=self.on_reflect, on_failure=self.on_failure)
