from django.http import HttpResponse
from django.template import loader

from findroute.models import DataInfo
from findroute.vrpSolver import VrpSolver
from .forms import UploadFileForm, CheckMultiCheckBox, HereApiForm
from django.core.files import File
import json
import os

VEHICLE_SPEED=1000
NUMBER_OF_TOTAL_CUSTOMERS_AND_DEPOT=276
NUMBER_OF_WORKING_DAYS_IN_A_WEEK=5
NUMBER_OF_WEEKS=2
NUMBER_OF_VEHICLES=1#per day
COLOUR_LIST=['Blue','Red','Orange','Green','SaddleBrown','DarkOrchid','Black','Grey','Violet','Navy']
DAY_LIST=['Monday', 'Tuesday', 'Wednesday','Thursday','Friday','Saturday','Sunday']

def index(request):
    template = loader.get_template('findroute/index.html')
    coordinatesfileuploader = UploadFileForm(label="Upload Coordinates file")
    coordinatesfileuploader.fields['file_field'].widget.attrs['id'] = "coordinatesfileuploader"
    distancesfileuploader = UploadFileForm(label="Upload distances file")
    distancesfileuploader.fields['file_field'].widget.attrs['id'] = "distancesfileuploader"
    routesfileuploader = UploadFileForm(label="Upload routes file")
    routesfileuploader.fields['file_field'].widget.attrs['id'] = "routesfileuploader"

    here_api_credentials=HereApiForm()
    context = {
        'coordinatesfileform': coordinatesfileuploader,
        'distancesfileform': distancesfileuploader,
        'hereapicredentials':here_api_credentials,
        'routesfileuploader':routesfileuploader
    }
    return HttpResponse(template.render(context, request))

def displayRoutes(request):

    uploadform = UploadFileForm(None,request.POST, request.FILES)
    hereform = HereApiForm(request.POST)
    if request.method == 'POST' and uploadform.is_valid() and hereform.is_valid():
        '''calculate_routes = False
        if len(request.FILES.getlist('file_field')) == 3:
            if str(request.FILES.getlist('file_field')[2]) == 'Input_route_example_time.xlsx':
                calculate_routes = False
            else:
                calculate_routes = True'''
        #if len(request.FILES.getlist('file_field')) == 2 or (len(request.FILES.getlist('file_field')) == 3 and calculate_routes):
        if len(request.FILES.getlist('file_field')) == 2:
            coordinatesfile = request.FILES.getlist('file_field')[0]
            distancesfile = request.FILES.getlist('file_field')[1]
            vrpSolver=VrpSolver(VEHICLE_SPEED,NUMBER_OF_TOTAL_CUSTOMERS_AND_DEPOT,NUMBER_OF_WORKING_DAYS_IN_A_WEEK,NUMBER_OF_WEEKS,NUMBER_OF_VEHICLES)
            routeComputation = vrpSolver.computeRoutes(coordinatesfile, distancesfile)
            routes = routeComputation[0]  # including depot
            route_summaries = routeComputation[1]
            for i in range(len(route_summaries)):
                for j in range(len(route_summaries[i])):
                    route_summaries[i][j][0] = "Distance: " + str(route_summaries[i][j][0]) + " meters"
                    route_summaries[i][j][1] = "Route duration " + str(route_summaries[i][j][1]) + " minutes"
                    route_summaries[i][j][2] = "Number of costumers: " + str(route_summaries[i][j][2])
            all_data = routeComputation[2]
            coords = [all_data[x]['gps_pos'] for x in range(len(all_data))]
        #if len(request.FILES.getlist('file_field')) == 1 or (len(request.FILES.getlist('file_field')) == 3 and not calculate_routes):
        if len(request.FILES.getlist('file_field')) == 1:
            try:
                routesfile = request.FILES.getlist('file_field')[0]
                route_summaries,coords=DataInfo.getRoutes(routesfile)
                routes = DataInfo.getRoutesFromXls(routesfile,coords)
                routes_multiple_lists=[]
                route_summaries_multiple_lists = []
                for i in range(2):
                    route_summaries_multiple_lists.append([])
                    routes_multiple_lists.append([])
                    for j in range(5):
                        route_summaries_multiple_lists[i].append(route_summaries[i*5+j])
                        route_summaries_multiple_lists[i][j][0] = "Distance: " + str(route_summaries[i*5+j][0]) + " meters"
                        if route_summaries[i*5+j][1]==None:
                            route_summaries_multiple_lists[i][j][1] = "Unavailable route duration"
                        else:
                            route_summaries_multiple_lists[i][j][1] = "Route duration: " + str(route_summaries[i * 5 + j][1]) + " minutes"

                        route_summaries_multiple_lists[i][j][2] = "Number of costumers: " + str(route_summaries[i*5+j][2])
                        routes_multiple_lists[i].append(routes[i * 5 + j])
                routes=routes_multiple_lists
                route_summaries=route_summaries_multiple_lists
            except Exception as ex:
                return HttpResponse('<h1>Error in filling the form</h1>')

        coords = json.dumps(coords)
        routechoices=[(str(i),'Week '+str(DataInfo.getWeekDayNumber(NUMBER_OF_WORKING_DAYS_IN_A_WEEK,NUMBER_OF_WEEKS,i)[0])+' - '+str(DAY_LIST[DataInfo.getWeekDayNumber(NUMBER_OF_WORKING_DAYS_IN_A_WEEK,NUMBER_OF_WEEKS,i)[1]-1])+' - '+COLOUR_LIST[i]) for i in range(NUMBER_OF_WEEKS*NUMBER_OF_WORKING_DAYS_IN_A_WEEK)]

        routeselectionmulticheck = CheckMultiCheckBox(routechoices=routechoices)
        here_app_id = hereform.data['here_app_id']
        here_app_code = hereform.data['here_app_code']
        template = loader.get_template('findroute/multiple_routes_here.html')
        context = {'route_summaries_dumps': json.dumps(route_summaries), 'route_all': json.dumps(routes),
                   'checkboxes': routeselectionmulticheck, 'coords': coords,
                   'here_app_id': here_app_id, 'here_app_code': here_app_code}
        return HttpResponse(template.render(context, request))
    else:
        return HttpResponse('<h1>Error in filling the form</h1>')