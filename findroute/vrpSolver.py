import datetime
import time
from findroute.googlerouting import GoogleTWVRP
from findroute.models import DataInfo,XlsData

class VrpSolver:
    def __init__(self, vehicle_speed,number_of_cust_and_depo,working_days_in_a_week,number_of_weeks,num_vehicles):
        self.vehicle_speed=vehicle_speed #meters per minute
        self.number_of_cust_and_depo=number_of_cust_and_depo
        self.working_days_in_a_week=working_days_in_a_week
        self.number_of_weeks=number_of_weeks
        self.num_vehicles=num_vehicles

    def computeRoutes(self,coordinates_file, distance_matrix_file):
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H-%M-%S')
        filename = "route_vrp_" + timestamp
        pos_and_freq= XlsData.getXlsDataStartOffset(coordinates_file,"G20",self.number_of_cust_and_depo-1,2)#2=3-1, -1 beacuse G20 is already at the depot
                                                                                                        # gps pos and frequence including depot
        tw_and_service_times = XlsData.getXlsDataStartOffset(coordinates_file, "KW20",self.number_of_cust_and_depo-1,
                                                             self.working_days_in_a_week*self.number_of_weeks*2)  # time windows and service times including depot
        coordinates_file.flush()
        coordinates_file.close()
        distances= XlsData.getXlsDataStartOffset(distance_matrix_file, "A1", self.number_of_cust_and_depo-1,self.number_of_cust_and_depo-1,
                                            list_of_lists=True)
        distance_matrix_file.flush()
        distance_matrix_file.close()
        all_data = DataInfo.get_all_transportation_data(pos_and_freq, tw_and_service_times, distances)
        week_1_2_customer_indices = DataInfo.get_week_1_2_customers_indices(all_data,self.number_of_weeks)
        week1_customers_indices = week_1_2_customer_indices["week1"]  # excluding depot, that will be added later
        week2_customers_indices = week_1_2_customer_indices["week2"]

        day_clusters = DataInfo.get_day_clusters(all_data, week1_customers_indices, week2_customers_indices)
        routes = {}
        route_summaries = {}
        for i in day_clusters.keys():
            routes[i] = {}
            route_summaries[i] = {}
            for j in day_clusters[i].keys():
                preproc = DataInfo.prepareRoutingData(all_data, day_clusters, i, j)
                cus_cord_and_depot = preproc["coord"]
                time_windows = preproc["time_windows"]
                ser_times = preproc["service_times"]
                dist = preproc["distances"]
                global_indices = preproc["global_indices"]
                googlerouter = GoogleTWVRP(cus_cord_and_depot, self.num_vehicles, time_windows, ser_times, self.vehicle_speed, dist, global_indices,
                                           i,
                                           j, filename)
                result_routing_computation = googlerouter.compute_routing()
                route = result_routing_computation[0]
                if not route:
                    raise Exception('Error in Google route computer')
                route_summary = result_routing_computation[1]
                routes[i][j] = {}
                routes[i][j][1] = route
                route_summaries[i][j] = route_summary

        GoogleTWVRP.routingFromTxtToCsvXlsx(filename)
        for i in range(len(routes)):
            for j in range(len(routes[i])):
                positions = DataInfo.getPositionsFromIndices(routes[i][j][1], all_data)
                routes[i][j][0] = positions
        return routes, route_summaries, all_data,filename