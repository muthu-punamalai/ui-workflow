import asyncio
import logging

from browser_use import Browser
from browser_use.agent.views import ActionResult
from browser_use.controller.service import Controller
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from workflow_use.controller.utils import get_best_element_handle, truncate_selector
from workflow_use.controller.views import (
	ClickElementDeterministicAction,
	InputTextDeterministicAction,
	KeyPressDeterministicAction,
	NavigationAction,
	PageExtractionAction,
	ScrollDeterministicAction,
	SelectDropdownOptionDeterministicAction,
)

logger = logging.getLogger(__name__)

DEFAULT_ACTION_TIMEOUT_MS = 5000  # Balanced 5 seconds for faster fallback with good reliability

# List of default actions from browser_use.controller.service.Controller to disable
# todo: come up with a better way to filter out the actions (filter IN the actions would be much nicer in this case)
DISABLED_DEFAULT_ACTIONS = [
	'done',
	'search_google',
	'go_to_url',  # I am using this action from the main controller to avoid duplication
	'go_back',
	'wait',
	'click_element_by_index',
	'input_text',
	'save_pdf',
	'switch_tab',
	'open_tab',
	'close_tab',
	'extract_content',
	'scroll_down',
	'scroll_up',
	'send_keys',
	'scroll_to_text',
	'get_dropdown_options',
	'select_dropdown_option',
	'drag_drop',
	'get_sheet_contents',
	'select_cell_or_range',
	'get_range_contents',
	'clear_selected_range',
	'input_selected_cell_text',
	'update_range_contents',
]


class WorkflowController(Controller):
	def __init__(self, *args, **kwargs):
		# Pass the list of actions to exclude to the base class constructor
		super().__init__(*args, exclude_actions=DISABLED_DEFAULT_ACTIONS, **kwargs)
		self.__register_actions()

	async def _wait_for_application_stability(self, action_type: str, element_info: str = ""):
		"""Universal method to wait for application to stabilize after any action"""
		import asyncio

		# Base wait for DOM updates
		await asyncio.sleep(0.5)

		# Wait for network stability (AJAX calls, API requests)
		try:
			await self.browser._wait_for_stable_network(timeout=3000)
			logger.debug(f"Network stabilized after {action_type}")
		except Exception as e:
			logger.debug(f"Network wait timeout after {action_type}: {e}")

		# Wait for any loading indicators to disappear
		try:
			page = await self.browser.get_current_page()

			# Common loading selectors
			loading_selectors = [
				'.loading', '.spinner', '[data-loading="true"]',
				'.css-loading', '[aria-busy="true"]', '.loader'
			]

			for selector in loading_selectors:
				try:
					await page.wait_for_selector(selector, state='hidden', timeout=2000)
					logger.debug(f"Loading indicator {selector} disappeared")
				except:
					continue  # Selector not found or already hidden

		except Exception as e:
			logger.debug(f"Loading indicator check failed: {e}")

		# Additional wait based on action type
		if action_type == 'click':
			# Check if this was a submit button or navigation-triggering element
			if 'submit' in element_info.lower() or 'login' in element_info.lower() or 'sign in' in element_info.lower():
				await asyncio.sleep(3.0)  # Extra time for form submission and page navigation
				logger.debug(f"Extended wait for submit/navigation button: {element_info}")
			else:
				await asyncio.sleep(1.5)  # Standard time for click reactions
		elif action_type == 'input':
			await asyncio.sleep(0.5)  # Time for input validation
		elif action_type == 'navigation':
			await asyncio.sleep(2)  # Time for page transitions

		logger.debug(f"Application stability wait completed for {action_type}")

	def __register_actions(self):
		# Navigate to URL ------------------------------------------------------------
		@self.registry.action('Manually navigate to URL', param_model=NavigationAction)
		async def navigation(params: NavigationAction, browser_session: Browser) -> ActionResult:
			"""Navigate to the given URL."""
			page = await browser_session.get_current_page()
			await page.goto(params.url)
			await page.wait_for_load_state()

			# Wait for application stability after navigation
			await self._wait_for_application_stability('navigation', params.url)

			msg = f'🔗  Navigated to URL: {params.url}'
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Click element by CSS selector --------------------------------------------------

		@self.registry.action(
			'Click element by all available selectors',
			param_model=ClickElementDeterministicAction,
		)
		async def click(params: ClickElementDeterministicAction, browser_session: Browser) -> ActionResult:
			"""Click the first element matching *params.cssSelector* with fallback mechanisms."""
			page = await browser_session.get_current_page()
			original_selector = params.cssSelector

			try:
				locator, selector_used = await get_best_element_handle(
					page,
					params.cssSelector,
					params,
					timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
				)
				await locator.click(force=True)

				# Wait for application stability after click
				await self._wait_for_application_stability('click', selector_used)

				msg = f'🖱️  Clicked element with CSS selector: {truncate_selector(selector_used)} (original: {truncate_selector(original_selector)})'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				error_msg = f'Failed to click element. Original selector: {truncate_selector(original_selector)}. Error: {str(e)}'
				logger.error(error_msg)
				raise Exception(error_msg)

		# Input text into element --------------------------------------------------------
		@self.registry.action(
			'Input text into an element by all available selectors',
			param_model=InputTextDeterministicAction,
		)
		async def input(
			params: InputTextDeterministicAction,
			browser_session: Browser,
			has_sensitive_data: bool = False,
		) -> ActionResult:
			"""Fill text into the element located with *params.cssSelector*."""
			page = await browser_session.get_current_page()
			original_selector = params.cssSelector

			try:
				locator, selector_used = await get_best_element_handle(
					page,
					params.cssSelector,
					params,
					timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
				)

				# Check if it's a SELECT element
				is_select = await locator.evaluate('(el) => el.tagName === "SELECT"')
				if is_select:
					return ActionResult(
						extracted_content='Ignored input into select element',
						include_in_memory=True,
					)

				# Ensure element is ready for interaction
				await locator.wait_for(state='visible', timeout=5000)
				await locator.scroll_into_view_if_needed()

				# Focus, clear, and fill the element
				await locator.click()  # Focus first
				await locator.clear()  # Clear existing content
				await locator.fill(params.value)  # Fill with new content

				# Verify the input was successful
				try:
					actual_value = await locator.input_value()
					if actual_value != params.value:
						logger.warning(f"Input verification failed. Expected: {params.value}, Actual: {actual_value}")
				except:
					pass  # Some elements might not support input_value()

				# Wait for application stability after input
				await self._wait_for_application_stability('input', selector_used)

				msg = f'⌨️  Input "{params.value}" into element with CSS selector: {truncate_selector(selector_used)} (original: {truncate_selector(original_selector)})'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				error_msg = f'Failed to input text. Original selector: {truncate_selector(original_selector)}. Error: {str(e)}'
				logger.error(error_msg)
				raise Exception(error_msg)

		# Select dropdown option ---------------------------------------------------------
		@self.registry.action(
			'Select dropdown option by all available selectors and visible text',
			param_model=SelectDropdownOptionDeterministicAction,
		)
		async def select_change(params: SelectDropdownOptionDeterministicAction, browser_session: Browser) -> ActionResult:
			"""Select dropdown option whose visible text equals *params.value*."""
			page = await browser_session.get_current_page()
			original_selector = params.cssSelector

			try:
				locator, selector_used = await get_best_element_handle(
					page,
					params.cssSelector,
					params,
					timeout_ms=DEFAULT_ACTION_TIMEOUT_MS,
				)

				await locator.select_option(label=params.selectedText)

				msg = f'Selected option "{params.selectedText}" in dropdown {truncate_selector(selector_used)} (original: {truncate_selector(original_selector)})'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				error_msg = f'Failed to select option. Original selector: {truncate_selector(original_selector)}. Error: {str(e)}'
				logger.error(error_msg)
				raise Exception(error_msg)

		# Key press action ------------------------------------------------------------
		@self.registry.action(
			'Press key on element by all available selectors',
			param_model=KeyPressDeterministicAction,
		)
		async def key_press(params: KeyPressDeterministicAction, browser_session: Browser) -> ActionResult:
			"""Press *params.key* on the element identified by *params.cssSelector*."""
			page = await browser_session.get_current_page()
			original_selector = params.cssSelector

			try:
				locator, selector_used = await get_best_element_handle(page, params.cssSelector, params, timeout_ms=5000)

				await locator.press(params.key)

				msg = f"🔑  Pressed key '{params.key}' on element with CSS selector: {truncate_selector(selector_used)} (original: {truncate_selector(original_selector)})"
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				error_msg = f'Failed to press key. Original selector: {truncate_selector(original_selector)}. Error: {str(e)}'
				logger.error(error_msg)
				raise Exception(error_msg)

		# Scroll action --------------------------------------------------------------
		@self.registry.action('Scroll page', param_model=ScrollDeterministicAction)
		async def scroll(params: ScrollDeterministicAction, browser_session: Browser) -> ActionResult:
			"""Scroll the page by the given x/y pixel offsets."""
			page = await browser_session.get_current_page()
			await page.evaluate(f'window.scrollBy({params.scrollX}, {params.scrollY});')
			msg = f'📜  Scrolled page by (x={params.scrollX}, y={params.scrollY})'
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

			# Extract content ------------------------------------------------------------

		@self.registry.action(
			'Extract page content to retrieve specific information from the page, e.g. all company names, a specific description, all information about, links with companies in structured format or simply links',
			param_model=PageExtractionAction,
		)
		async def extract_page_content(
			params: PageExtractionAction, browser_session: Browser, page_extraction_llm: BaseChatModel
		):
			page = await browser_session.get_current_page()
			import markdownify

			strip = ['a', 'img']

			content = markdownify.markdownify(await page.content(), strip=strip)

			# manually append iframe text into the content so it's readable by the LLM (includes cross-origin iframes)
			for iframe in page.frames:
				if iframe.url != page.url and not iframe.url.startswith('data:'):
					content += f'\n\nIFRAME {iframe.url}:\n'
					content += markdownify.markdownify(await iframe.content())

			prompt = 'Your task is to extract the content of the page. You will be given a page and a goal and you should extract all relevant information around this goal from the page. If the goal is vague, summarize the page. Respond in json format. Extraction goal: {goal}, Page: {page}'
			template = PromptTemplate(input_variables=['goal', 'page'], template=prompt)
			try:
				formatted_prompt = template.format(goal=params.goal, page=content)
				output = await page_extraction_llm.ainvoke(formatted_prompt)

				# Track token usage for page extraction
				try:
					from workflow_use.hybrid.token_tracker import track_llm_call
					# Estimate token usage for page extraction
					input_tokens = len(formatted_prompt.split()) * 1.3
					output_tokens = len(output.content.split()) * 1.3
					model_name = getattr(page_extraction_llm, 'model_name', 'page-extraction-llm')
					track_llm_call(model_name, int(input_tokens), int(output_tokens))
					logger.debug(f"Tracked page extraction: {int(input_tokens + output_tokens)} tokens")
				except Exception as e:
					logger.debug(f"Token tracking failed for page extraction: {e}")

				msg = f'📄  Extracted from page\n: {output.content}\n'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				logger.debug(f'Error extracting content: {e}')
				msg = f'📄  Extracted from page\n: {content}\n'
				logger.info(msg)
				return ActionResult(extracted_content=msg)
