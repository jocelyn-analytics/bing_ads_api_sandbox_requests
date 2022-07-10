from bingads.service_client import ServiceClient
from bingads.authorization import AuthorizationData, OAuthDesktopMobileAuthCodeGrant

import sys
import webbrowser
from time import gmtime, strftime
from suds import WebFault

# Required
CLIENT_ID = '4c0b021c-00c3-4508-838f-d3127e8167ff'
DEVELOPER_TOKEN='BBD37VB98'
ENVIRONMENT='sandbox'
REFRESH_TOKEN="refresh.txt"

# Optional
CLIENT_STATE='ClientStateGoesHere'

# Optionally you can include logging to output traffic, for example the SOAP request and response.
import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)
logging.getLogger('suds.transport.http').setLevel(logging.DEBUG)

def authenticate(authorization_data):

    customer_service=ServiceClient(
        service='CustomerManagementService', 
        version=13,
        authorization_data=authorization_data, 
        environment=ENVIRONMENT,
    )

    # You should authenticate for Bing Ads API service operations with a Microsoft Account.
    authenticate_with_oauth(authorization_data)

    # Set to an empty user identifier to get the current authenticated Microsoft Advertising user,
    # and then search for all accounts the user can access.
    user=get_user_response=customer_service.GetUser(
        UserId=None
    ).User
    accounts=search_accounts_by_user_id(customer_service, user.Id)

    # For this example we'll use the first account.
    authorization_data.account_id=accounts['AdvertiserAccount'][0].Id
    authorization_data.customer_id=accounts['AdvertiserAccount'][0].ParentCustomerId

def authenticate_with_oauth(authorization_data):

    authentication=OAuthDesktopMobileAuthCodeGrant(
        client_id=CLIENT_ID,
        env=ENVIRONMENT
    )

    # It is recommended that you specify a non guessable 'state' request parameter to help prevent
    # cross site request forgery (CSRF). 
    authentication.state=CLIENT_STATE

    # Assign this authentication instance to the authorization_data. 
    authorization_data.authentication=authentication   

    # Register the callback function to automatically save the refresh token anytime it is refreshed.
    # Uncomment this line if you want to store your refresh token. Be sure to save your refresh token securely.
    authorization_data.authentication.token_refreshed_callback=save_refresh_token

    refresh_token=get_refresh_token()

    try:
        # If we have a refresh token let's refresh it
        if refresh_token is not None:
            authorization_data.authentication.request_oauth_tokens_by_refresh_token(refresh_token)
        else:
            request_user_consent(authorization_data)
    except OAuthTokenRequestException:
        # The user could not be authenticated or the grant is expired. 
        # The user must first sign in and if needed grant the client application access to the requested scope.
        request_user_consent(authorization_data)

def request_user_consent(authorization_data):
    webbrowser.open(authorization_data.authentication.get_authorization_endpoint(), new=1)
    # For Python 3.x use 'input' instead of 'raw_input'
    if(sys.version_info.major >= 3):
        response_uri=input(
            "You need to provide consent for the application to access your Microsoft Advertising accounts. " \
            "After you have granted consent in the web browser for the application to access your Microsoft Advertising accounts, " \
            "please enter the response URI that includes the authorization 'code' parameter: \n"
        )
    else:
        response_uri=raw_input(
            "You need to provide consent for the application to access your Microsoft Advertising accounts. " \
            "After you have granted consent in the web browser for the application to access your Microsoft Advertising accounts, " \
            "please enter the response URI that includes the authorization 'code' parameter: \n"
        )

    if authorization_data.authentication.state != CLIENT_STATE:
        raise Exception("The OAuth response state does not match the client request state.")

    # Request access and refresh tokens using the URI that you provided manually during program execution.
    authorization_data.authentication.request_oauth_tokens_by_response_uri(response_uri=response_uri) 

def get_refresh_token():
    ''' 
    Returns a refresh token if found.
    '''
    file=None
    try:
        file=open(REFRESH_TOKEN)
        line=file.readline()
        file.close()
        return line if line else None
    except IOError:
        if file:
            file.close()
        return None

def save_refresh_token(oauth_tokens):
    ''' 
    Stores a refresh token locally. Be sure to save your refresh token securely.
    '''
    with open(REFRESH_TOKEN,"w+") as file:
        file.write(oauth_tokens.refresh_token)
        file.close()
    return None

def search_accounts_by_user_id(customer_service, user_id):
    predicates={
        'Predicate': [
            {
                'Field': 'UserId',
                'Operator': 'Equals',
                'Value': user_id,
            },
        ]
    }

    accounts=[]

    page_index = 0
    PAGE_SIZE=100
    found_last_page = False

    while (not found_last_page):
        paging=set_elements_to_none(customer_service.factory.create('ns5:Paging'))
        paging.Index=page_index
        paging.Size=PAGE_SIZE
        search_accounts_response = customer_service.SearchAccounts(
            PageInfo=paging,
            Predicates=predicates
        )

        if search_accounts_response is not None and hasattr(search_accounts_response, 'AdvertiserAccount'):
            accounts.extend(search_accounts_response['AdvertiserAccount'])
            found_last_page = PAGE_SIZE > len(search_accounts_response['AdvertiserAccount'])
            page_index += 1
        else:
            found_last_page=True

    return {
        'AdvertiserAccount': accounts
    }

def set_elements_to_none(suds_object):
    for (element) in suds_object:
        suds_object.__setitem__(element[0], None)
    return suds_object

def output_status_message(message):
    print(message)

def output_bing_ads_webfault_error(error):
    if hasattr(error, 'ErrorCode'):
        output_status_message("ErrorCode: {0}".format(error.ErrorCode))
    if hasattr(error, 'Code'):
        output_status_message("Code: {0}".format(error.Code))
    if hasattr(error, 'Details'):
        output_status_message("Details: {0}".format(error.Details))
    if hasattr(error, 'FieldPath'):
        output_status_message("FieldPath: {0}".format(error.FieldPath))
    if hasattr(error, 'Message'):
        output_status_message("Message: {0}".format(error.Message))
    output_status_message('')

def output_webfault_errors(ex):
    if not hasattr(ex.fault, "detail"):
        raise Exception("Unknown WebFault")

    error_attribute_sets = (
        ["ApiFault", "OperationErrors", "OperationError"],
        ["AdApiFaultDetail", "Errors", "AdApiError"],
        ["ApiFaultDetail", "BatchErrors", "BatchError"],
        ["ApiFaultDetail", "OperationErrors", "OperationError"],
        ["EditorialApiFaultDetail", "BatchErrors", "BatchError"],
        ["EditorialApiFaultDetail", "EditorialErrors", "EditorialError"],
        ["EditorialApiFaultDetail", "OperationErrors", "OperationError"],
    )

    for error_attribute_set in error_attribute_sets:
        if output_error_detail(ex.fault.detail, error_attribute_set):
            return

    # Handle serialization errors, for example: The formatter threw an exception while trying to deserialize the message, etc.
    if hasattr(ex.fault, 'detail') \
        and hasattr(ex.fault.detail, 'ExceptionDetail'):
        api_errors=ex.fault.detail.ExceptionDetail
        if isinstance(api_errors, list):
            for api_error in api_errors:
                output_status_message(api_error.Message)
        else:
            output_status_message(api_errors.Message)
        return

    raise Exception("Unknown WebFault")

def output_error_detail(error_detail, error_attribute_set):
    api_errors = error_detail
    for field in error_attribute_set:
        api_errors = getattr(api_errors, field, None)
    if api_errors is None:
        return False
    if isinstance(api_errors, list):
        for api_error in api_errors:
            output_bing_ads_webfault_error(api_error)
    else:
        output_bing_ads_webfault_error(api_errors)
    return True