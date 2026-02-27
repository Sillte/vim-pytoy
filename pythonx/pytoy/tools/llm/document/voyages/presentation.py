from pytoy.ui.pytoy_buffer import make_buffer
from pytoy.infra.timertask import ThreadWorker
from pytoy.tools.llm.pytoy_fairy import PytoyFairy, FairyKernel
from pytoy.tools.llm.document.voyages.domain import Compass, EvolvePolicy, Bearing, CompassAlignment
from pytoy.tools.llm.document.voyages.application import EvolveRequest, EvolveResponse, ReflectRequest, ReflectResponse, VoyageInteractionCreator
from pytoy.tools.llm.utils import TomlConverter
from pytoy.ui.notifications import EphemeralNotification
from typing import Mapping, Any


class DocumentVoyageUI:
    def __init__(self, pytoy_fairy: PytoyFairy,
                       directive_buffer_name: str = "voyage", 
                      ):
        self._pytoy_fairy = pytoy_fairy
        self._interaction_creator = VoyageInteractionCreator(self._pytoy_fairy.kernel)
        self._directive_buffer_name = directive_buffer_name
        self._toml_converter = TomlConverter()
        self._toml_class_map = {"compass": Compass, "evolve_policy": EvolvePolicy, "bearing": Bearing}
        
    @property
    def pytoy_fairy(self) -> PytoyFairy:
        return self._pytoy_fairy
    
    @property
    def manuscript(self) -> str:
        """Get the manuscript.
        """
        return self.pytoy_fairy.buffer.content
    

    def _from_basemodels(self, basemodels: Mapping[str, Any]) -> tuple[Compass, EvolvePolicy, Bearing]:
        return (basemodels["compass"],  basemodels["evolve_policy"], basemodels["bearing"])
    
    def _to_basemodels(self, compass: Compass, evolve_policy: EvolvePolicy, bearing: Bearing) -> Mapping[str, Any]:
        return {"compass": compass, "evolve_policy": evolve_policy, "bearing": bearing}

    
    def _complete_states(self) -> tuple[Compass, EvolvePolicy, Bearing]:
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        toml_text = directive_buffer.content
        default_basemodels = {"compass": Compass(progress="emerging", objective="Please fulfill my objective."),
                      "evolve_policy": EvolvePolicy(degree="auto", comment="Make a good document."),
                      "bearing": Bearing(alignment=CompassAlignment(state="undefined", reason="Uncertain compass"), assessment="N/A")
                      }
        try:
            basemodels = self._toml_converter.to_basemodels(toml_text, self._toml_class_map)
        except (ValueError):
            basemodels = default_basemodels
        else:
            basemodels = {key: basemodels.get(key, default_basemodels[key]) for key in default_basemodels.keys()}
        
        return self._from_basemodels(basemodels)
    
    def on_failure(self, exception: Exception):
        self.pytoy_fairy.llm_context.logger.info(f"Exception:{exception}")
        ThreadWorker.add_message(str(exception))
        EphemeralNotification().notify("Error happens. See `log` or `:messages`.")
    
    def on_evolve(self, evolve_response: EvolveResponse) -> None:
        self.pytoy_fairy.llm_context.logger.info(f"EvolveResponse:{evolve_response}")
        compass, evolve_policy, bearing = self._complete_states()
        basemodels = self._to_basemodels(evolve_response.compass, evolve_policy, bearing)
        directive_content = self._toml_converter.from_basemodels(basemodels)
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        directive_buffer.init_buffer(directive_content)
        self.pytoy_fairy.buffer.init_buffer(evolve_response.manuscript)

    
    def _construct_evolve_request(self) -> EvolveRequest:
        compass, evolve_policy, bearing = self._complete_states()
        manuscript = self.pytoy_fairy.buffer.content
        evolve_request = EvolveRequest(compass=compass, evolve_policy=evolve_policy, manuscript=manuscript)
        self.pytoy_fairy.llm_context.logger.info("EvolveRequest:" +  str(evolve_request))
        return evolve_request

    
    def _construct_reflect_request(self) -> ReflectRequest:
        compass, evolve_policy, bearing = self._complete_states()
        manuscript = self.pytoy_fairy.buffer.content
        reflect_request= ReflectRequest(manuscript=manuscript, compass=compass)
        self.pytoy_fairy.llm_context.logger.info("ReflectRequest:" +  str(reflect_request))
        return reflect_request

    def on_reflect(self, reflect_response: ReflectResponse) -> None:
        self.pytoy_fairy.llm_context.logger.info(f"ReflectResponse:{reflect_response}")
        compass, evolve_policy, bearing = self._complete_states()
        basemodels = self._to_basemodels(reflect_response.compass, evolve_policy, reflect_response.bearing)
        directive_content = self._toml_converter.from_basemodels(basemodels)
        directive_buffer = make_buffer(self._directive_buffer_name, mode="vertical")
        directive_buffer.init_buffer(directive_content)
    
    def evolve(self):
        evolve_request = self._construct_evolve_request()
        self._interaction_creator.create_evolve_interaction(evolve_request, on_success=self.on_evolve, on_failure=self.on_failure)

    def reflect(self):
        reflect_request = self._construct_reflect_request()
        self._interaction_creator.create_reflect_interaction(reflect_request, on_success=self.on_reflect, on_failure=self.on_failure)