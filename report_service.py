from datetime import datetime
from oauth import *
from bingads.v13.reporting import *
from bingads.service_client import ServiceClient
from bingads.authorization import AuthorizationData, OAuthDesktopMobileAuthCodeGrant
import pandas as pd

# You must provide credentials in oauth.py.

# The report file extension type.
REPORT_FILE_FORMAT='Csv'

# The directory for the report files.
FILE_DIRECTORY='/Users/jocelynchan/Dev/api/reports/'

# The name of the report download file.
date = datetime.now().strftime("%Y_%m_%d")
RESULT_FILE_NAME= 'result_' + date + '.' + REPORT_FILE_FORMAT.lower()

# The maximum amount of time (in milliseconds) that you want to wait for the report download.
TIMEOUT_IN_MILLISECONDS=3600000

def main(authorization_data):
    try:
        # You can submit one of the example reports, or build your own.

        report_request=get_report_request(authorization_data.account_id)
        
        reporting_download_parameters = ReportingDownloadParameters(
            report_request=report_request,
            result_file_directory = FILE_DIRECTORY, 
            result_file_name = RESULT_FILE_NAME, 
            overwrite_result_file = False, # Set this value true if you want to overwrite the same file.
            timeout_in_milliseconds=TIMEOUT_IN_MILLISECONDS # You may optionally cancel the download after a specified time interval.
        )

        #Download the report in memory with ReportingServiceManager.download_report
        #The download_report helper function downloads the report and summarizes results.
        output_status_message("-----\nAwaiting download_report...")
        download_report(reporting_download_parameters)
    except WebFault as ex:
        output_webfault_errors(ex)
    except Exception as ex:
        output_status_message(ex)


def download_report(reporting_download_parameters):
    """ You can get a Report object by submitting a new download request via ReportingServiceManager. 
    Although in this case you will not work directly with the file, under the covers a request is 
    submitted to the Reporting service and the report file is downloaded to a local directory.  """
    
    global reporting_service_manager

    report_container = reporting_service_manager.download_report(reporting_download_parameters)

    if(report_container == None):
        output_status_message("There is no report data for the submitted report request parameters.")
        sys.exit(0)

    #Once you have a Report object via either workflow above, you can access the metadata and report records. 

    #Output the report metadata

    record_count = report_container.record_count
    output_status_message("ReportName: {0}".format(report_container.report_name))
    output_status_message("ReportTimeStart: {0}".format(report_container.report_time_start))
    output_status_message("ReportTimeEnd: {0}".format(report_container.report_time_end))
    output_status_message("LastCompletedAvailableDate: {0}".format(report_container.last_completed_available_date))
    output_status_message("ReportAggregation: {0}".format(report_container.report_aggregation))
    output_status_message("ReportColumns: {0}".format("; ".join(str(column) for column in report_container.report_columns)))
    output_status_message("ReportRecordCount: {0}".format(record_count))

    #Analyze and output performance statistics

    if "Impressions" in report_container.report_columns and \
        "Clicks" in report_container.report_columns:

        report_record_iterable = report_container.report_records

        total_impressions = 0
        total_clicks = 0
        total_spend = 0 
        distinct_devices = set()
        distinct_networks = set()
        for record in report_record_iterable:
            total_impressions += record.int_value("Impressions")
            total_clicks += record.int_value("Clicks")
            total_spend += record.float_value("Spend")
            distinct_devices.add(record.value("DeviceType"))
            distinct_networks.add(record.value("Network"))

        output_status_message("Total Impressions: {0}".format(total_impressions))
        output_status_message("Total Clicks: {0}".format(total_clicks))
        output_status_message("Total Spend: {0}".format(total_spend))
        output_status_message("Average Impressions: {0}".format(total_impressions * 1.0 / record_count))
        output_status_message("Average Clicks: {0}".format(total_clicks * 1.0 / record_count))
        output_status_message("Average Spend: {0}".format(total_spend * 1.0 / record_count))
        output_status_message("Distinct Devices: {0}".format("; ".join(str(device) for device in distinct_devices)))
        output_status_message("Distinct Networks: {0}".format("; ".join(str(network) for network in distinct_networks)))

    #read the downloaded report as a dataframe
    pd.set_option('display.max_columns', 100)
    file_path = reporting_download_parameters.result_file_directory + reporting_download_parameters.result_file_name
    df = pd.read_csv(file_path, header=9, skipfooter=2, engine='python')
    print(df)
    
    #Be sure to close the report.
    report_container.close()

def get_report_request(account_id):
    """ 
    Use a sample report request or build your own. 
    """

    aggregation = 'Daily'
    exclude_column_headers=False
    exclude_report_footer=False
    exclude_report_header=False
    time=reporting_service.factory.create('ReportTime')
    # You can either use a custom date range or predefined time.
    time.PredefinedTime='Last30Days'
    time.ReportTimeZone='EasternTimeUSCanada'
    time.CustomDateRangeStart = None
    time.CustomDateRangeEnd = None
    return_only_complete_data=False

    campaign_performance_report_request=get_campaign_performance_report_request(
        account_id=account_id,
        aggregation=aggregation,
        exclude_column_headers=exclude_column_headers,
        exclude_report_footer=exclude_report_footer,
        exclude_report_header=exclude_report_header,
        report_file_format=REPORT_FILE_FORMAT,
        return_only_complete_data=return_only_complete_data,
        time=time)

    return campaign_performance_report_request


def get_campaign_performance_report_request(
        account_id,
        aggregation,
        exclude_column_headers,
        exclude_report_footer,
        exclude_report_header,
        report_file_format,
        return_only_complete_data,
        time):

    report_request=reporting_service.factory.create('CampaignPerformanceReportRequest')
    report_request.Aggregation=aggregation
    report_request.ExcludeColumnHeaders=exclude_column_headers
    report_request.ExcludeReportFooter=exclude_report_footer
    report_request.ExcludeReportHeader=exclude_report_header
    report_request.Format=report_file_format
    report_request.ReturnOnlyCompleteData=return_only_complete_data
    report_request.Time=time    
    report_request.ReportName="My Campaign Performance Report"
    scope=reporting_service.factory.create('AccountThroughCampaignReportScope')
    scope.AccountIds={'long': [account_id] }
    scope.Campaigns=None
    report_request.Scope=scope     

    #documentation: https://docs.microsoft.com/en-us/advertising/reporting-service/campaignperformancereportcolumn?view=bingads-13
    report_columns=reporting_service.factory.create('ArrayOfCampaignPerformanceReportColumn')
    report_columns.CampaignPerformanceReportColumn.append([
        'TimePeriod',
        'AccountName',
        'AccountStatus',
        'CampaignId',
        'CampaignName',
        'CampaignStatus',
        'CampaignType',
        'DeliveredMatchType',
        'AdDistribution',
        'QualityScore',
        'Impressions',
        'Clicks',  
        'Ctr',
        'AverageCpc',
        'Spend',
        'ImpressionSharePercent',
        'TopImpressionRatePercent',
        'AbsoluteTopImpressionRatePercent',
        'Conversions',
        'ConversionRate',
        'CostPerConversion',
        'TrackingTemplate',
        'CustomParameters',
        #Below are new variables added for future reporting use
        'DeviceType',
        'Network',
        'Revenue',
        'ViewThroughConversions',
        'PhoneImpressions',
        'PhoneCalls',
        'ImpressionLostToRankAggPercent',
        'ImpressionLostToBudgetPercent',
        'AveragePosition',
    ])
    report_request.Columns=report_columns
    
    return report_request

# Main execution
if __name__ == '__main__':

    print("Loading the web service client proxies...")

    authorization_data=AuthorizationData(
        account_id=None,
        customer_id=None,
        developer_token=DEVELOPER_TOKEN,
        authentication=None,
    )

    reporting_service_manager=ReportingServiceManager(
        authorization_data=authorization_data, 
        poll_interval_in_milliseconds=5000, 
        environment=ENVIRONMENT,
    )

    # In addition to ReportingServiceManager, you will need a reporting ServiceClient 
    # to build the ReportRequest.

    reporting_service=ServiceClient(
        service='ReportingService', 
        version=13,
        authorization_data=authorization_data, 
        environment=ENVIRONMENT,
    )

    authenticate(authorization_data)
        
    main(authorization_data)



