import onnyx
from onnyx.onnyx import FailureCode, BaseFailureCodes
import subprocess

# Define custom failure codes
class FailureCodes(FailureCode):
    NO_FAILURE = BaseFailureCodes.NO_FAILURE
    EXCEPTION = BaseFailureCodes.EXCEPTION
    INTERNET_CONNECTION_FAILED = (-1, "Internet connection failed")

@onnyx.test()
def check_internet_connection(
    category: str,
    test_name: str,
    ping_url: str = "https://www.google.com",
):
    ping_results = []
    try:
        ping_results = subprocess.check_output(["ping", "-c", "5", ping_url])
        return onnyx.TestResult(
            "Internet connection successful",
            FailureCodes.NO_FAILURE,
            return_value={"ping_results": ping_results}
        )
    except Exception as e:
        return onnyx.TestResult(
            f"Internet connection failed: {str(e)}",
            FailureCodes.INTERNET_CONNECTION_FAILED,
            return_value={"ping_results": ping_results}
        )


def example_flow(test_document, settings):

    cellConfig = test_document["_cell_config_obj"]

    with onnyx.test_context(
        onnyx.TestContext.initialize(
            settings, test_document, FailureCodes.get_descriptions()
        )
    ) as test_context:
        test_context.logger.info("Starting example tests")
        failure_code = FailureCodes.NO_FAILURE

        rc = check_internet_connection(
            "Network",
            "Check internet connection",
            cellConfig.get("ping_url", "https://www.google.com"),
        )
        if rc.failure_code != FailureCodes.NO_FAILURE:
            failure_code = rc.failure_code
        else:
            test_context.record_values(rc.return_value)

        test_context.wrap_up(failure_code)
