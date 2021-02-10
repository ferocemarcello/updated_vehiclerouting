from ortools.constraint_solver import pywrapcp
import calendar
import openpyxl
import csv

class GoogleTWVRP:
    def __init__(self, customers_and_depot, num_vehicles, time_windows, service_times, speed, distances,global_indices,week,day,filename):
        self.locations = customers_and_depot
        self.num_vehicles= num_vehicles
        self.time_windows=time_windows
        self.service_times=service_times
        self.speed=speed
        self.distances=distances
        self.time_matrix = self.time_matrix_from_distance_matrix(self.distances)
        self.global_indices=global_indices
        self.week=week
        self.day=day
        self.filename=filename

    def getRoutingIndices(self,solution, routing, manager,global_indices):  # for one vehicle only
        index = routing.Start(0)
        routingIndices = []
        while not routing.IsEnd(index):
            node_index=manager.IndexToNode(index)
            routingIndices.append(global_indices[node_index])
            index = solution.Value(routing.NextVar(index))

        node_index = manager.IndexToNode(index)
        routingIndices.append(global_indices[node_index])
        return routingIndices

    def create_data_model(self):
        """Stores the data for the problem"""
        data = {}

        data["locations"] = self.locations
        data["num_locations"] = len(data["locations"])
        data["num_vehicles"] = self.num_vehicles
        data["depot"] = 0
        data["time_windows"] = self.time_windows
        for i in range(0,len(data["time_windows"])):#including depot
            if data["time_windows"][i][1]==0:
                lst=list(data["time_windows"][i])
                lst[1]=3000
                data["time_windows"][i]=tuple(lst)
        data["service_times"]=self.service_times
        data["vehicle_speed"] = self.speed
        data["distances"]=self.distances
        data["time_matrix"]=self.time_matrix
        return data

    #######################
    # Problem Constraints #
    #######################
    def create_time_callback(self,data):
        """Creates callback to get total times between locations."""

        def service_time(node):
            """Gets the service time for the specified location."""
            return data["service_times"][node]

        def travel_time(from_node, to_node):
            """Gets the travel times between two locations."""
            if from_node == to_node:
                travel_time = 0
            else:
                travel_time=(data["distances"][from_node][to_node])/data["vehicle_speed"]
            return travel_time

        def time_callback(from_node, to_node):
            """Returns the total time between the two nodes"""
            if from_node==to_node:
                return 0
            serv_time = service_time(from_node)
            trav_time = travel_time(from_node, to_node)
            return int(serv_time + trav_time)

        return time_callback

    def add_time_window_constraints(self,routing, data, time_callback):
        """Add Global Span constraint"""
        time = "Time"
        waiting_time_vehicle_horizon = 10

        max_min_tw=0
        try:
            for tw in data["time_windows"]:
                if tw[0] > max_min_tw:
                    max_min_tw = tw[0]
            max_time_vehicle_horizon = 540 + max_min_tw  # doesn't mean max time length to do all the route. It means the max time(minutes after midnight)
            # so in this case I say that it shouldn't take more than 9 hours after the time of the latest opening of the customers
        except Exception as ex:
            print(ex)
        routing.AddDimension(
            time_callback,
            waiting_time_vehicle_horizon,  # allow waiting time
            max_time_vehicle_horizon,  # maximum time per vehicle
            False,  # Don't force start cumul to zero. This doesn't have any effect here since the depot has a start window of (0, 0).
            time)
        time_dimension = routing.GetDimensionOrDie(time)
        for location_node, location_time_window in enumerate(data["time_windows"]):
            index = routing.NodeToIndex(location_node)
            try:
                time_dimension.CumulVar(index).SetRange(location_time_window[0], location_time_window[1])
            except Exception as ex:
                print(index<routing.nodes())
                print(time_dimension.CumulVar(index).Max()>=time_dimension.CumulVar(index).Min())
                print("time window error")
                print(ex)

    ###########
    # Printer #
    ###########
    def print_solution(self, data, routing, solution, manager, filename, local_positions, global_indices, week, day):
        """Prints assignment on console"""
        # Inspect solution.
        #capacity_dimension = routing.GetDimensionOrDie('Capacity')
        time_dimension = routing.GetDimensionOrDie('Time')
        total_dist = 0
        time_matrix = 0
        file_plan_output = 'Week {0}; day:{1}:\n'.format(week+1,calendar.day_name[day])
        for vehicle_id in range(data["num_vehicles"]):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {0}:\n'.format(vehicle_id)
            file_plan_output += 'Route for vehicle {0}:\n'.format(vehicle_id)
            route_dist = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                next_node_index = manager.IndexToNode(
                    solution.Value(routing.NextVar(index)))
                route_dist += data["distances"][node_index][next_node_index]
                #load_var = capacity_dimension.CumulVar(index)
                #route_load = assignment.Value(load_var)
                time_var = time_dimension.CumulVar(index)
                time_min = solution.Min(time_var)
                time_max = solution.Max(time_var)
                '''plan_output += ' {0} Load({1}) Time({2},{3}) ->'.format(
                    node_index,
                    route_load,
                    time_min, time_max)'''
                plan_output += ' {0} Time({1},{2}) ->'.format(
                    node_index,
                    time_min, time_max)
                all_data_index=global_indices[node_index]
                position=local_positions[node_index]
                file_plan_output+= ' {0} {1} Time({2},{3}) ->'.format(
                    all_data_index,position,
                    time_min, time_max)
                index = solution.Value(routing.NextVar(index))

            node_index = manager.IndexToNode(index)
            #load_var = capacity_dimension.CumulVar(index)
            #route_load = assignment.Value(load_var)
            time_var = time_dimension.CumulVar(index)
            route_time = solution.Value(time_var)
            time_min = solution.Min(time_var)
            time_max = solution.Max(time_var)
            total_dist += route_dist
            time_matrix += route_time
            '''plan_output += ' {0} Load({1}) Time({2},{3})\n'.format(node_index, route_load,
                                                                   time_min, time_max)'''
            plan_output += ' {0} Time({1},{2})\n'.format(node_index,
                                                                   time_min, time_max)
            plan_output += 'Distance of the route: {0} m\n'.format(route_dist)
            #plan_output += 'Load of the route: {0}\n'.format(route_load)
            plan_output += 'Time of the route: {0} min\n'.format(route_time)
            all_data_index = global_indices[node_index]
            position = local_positions[node_index]
            file_plan_output += ' {0} {1} Time({2},{3})\n'.format(all_data_index,position,
                                                         time_min, time_max)
            file_plan_output += 'Distance of the route: {0} m\n'.format(route_dist)
            # plan_output += 'Load of the route: {0}\n'.format(route_load)
            file_plan_output += 'Time of the route: {0} min\n'.format(route_time)
            file_plan_output += 'Number of customers: {0}\n'.format(data["num_locations"]-1)
            print(plan_output)
            with open(filename+".txt", "a") as text_file:
                print(file_plan_output, file=text_file)
            text_file.close()
        print('Total Distance of all routes: {0} m'.format(total_dist))
        print('Total Time of all routes: {0} min'.format(time_matrix))
        return [total_dist,time_matrix,data["num_locations"]-1]

    def compute_routing(self):
        """Entry point of the program"""
        # Instantiate the data problem.
        data = self.create_data_model()

        # Create the routing index manager.
        manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                               data['num_vehicles'], data['depot'])
        routing = pywrapcp.RoutingModel(manager)

        # Create and register a transit callback.
        def time_callback(from_index, to_index):
            """Returns the travel time between the two nodes."""
            # Convert from routing variable Index to time matrix NodeIndex.
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['time_matrix'][from_node][to_node]+data["service_times"][from_node]

        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        # Define cost of each arc.
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        # Add Capacity constraint
        #demand_callback = self.create_demand_callback(data)
        #self.add_capacity_constraints(routing, data, demand_callback)
        # Add Time Windows constraint.
        max_min_tw = 0
        for tw in data["time_windows"]:
            if tw[0] > max_min_tw:
                max_min_tw = tw[0]
        max_time_vehicle_horizon = 540 + max_min_tw  # doesn't mean max time length to do all the route. It means the max time(minutes after midnight)
        # so in this case I say that it shouldn't take more than 9 hours after the time of the latest opening of the customers
        time = 'Time'
        routing.AddDimension(
            transit_callback_index,
            10,  # allow waiting time
            max_time_vehicle_horizon,  # maximum time per vehicle
            False,  # Don't force start cumul to zero.
            time)

        time_dimension = routing.GetDimensionOrDie(time)

        # Add time window constraints for each location except depot.
        for location_idx, time_window in enumerate(data['time_windows']):
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
        # Add time window constraints for each vehicle start node.
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            time_dimension.CumulVar(index).SetRange(data['time_windows'][0][0],
                                                    data['time_windows'][0][1])

        # Instantiate route start and end times to produce feasible times.
        for i in range(data['num_vehicles']):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(i)))
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.End(i)))

        # Setting first solution heuristic (cheapest addition).
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        #search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.SAVINGS)
        #search_parameters.solution_limit = 1
        #search_parameters.optimization_step=15
        search_parameters.time_limit.seconds=20
        '''search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING)'''
        # Solve the problem.
        try:
            solution = routing.SolveWithParameters(search_parameters)
            if solution:
                routesummary=self.print_solution(data, routing, solution,manager,self.filename,data["locations"],self.global_indices,self.week,self.day)
                routing_indices=self.getRoutingIndices(solution,routing,manager,self.global_indices)
                return routing_indices,routesummary
        except Exception as ex:
            print("solver fail")
            print(ex)
            return False

    @classmethod
    def routingFromTxtToCsvXlsx(cls,filename):
        with open(filename+'.txt', 'r') as in_file:
            stripped = (line.strip() for line in in_file)
            lines = (line.split("->") for line in stripped if line)
            with open(filename+'.csv', 'w') as out_file:
                writer = csv.writer(out_file)
                #writer.writerow(('title', 'intro'))
                writer.writerows(lines)
        wb = openpyxl.Workbook()
        ws = wb.active
        with open(filename + '.csv', 'r') as f:
            for row in csv.reader(f):
                ws.append(row)
        wb.save(filename + '.xlsx')
        in_file.close()
        out_file.close()
        f.close()

    def time_matrix_from_distance_matrix(self, distances):
        time_matrix=len(distances)*[None]
        for i in range(len(distances)):
            time_matrix[i]=len(distances[i])*[None]
            for j in range(len(distances[i])):
                time_matrix[i][j]=distances[i][j]/self.speed#minutes
        return time_matrix