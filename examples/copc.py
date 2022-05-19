from laspy import CopcReader, Bounds
import time
import laspy

def create_query(header):
    querys = []

    sizes = header.maxs - header.mins

    # Bottom left
    query_bounds = Bounds(
        mins=header.mins,
        maxs=header.mins + sizes / 2
    )
    query_bounds.maxs[2] = header.maxs[2]
    querys.append(query_bounds)

    # Top Right
    # Bounds can also be 2D (then all Z are considered)
    query_bounds = Bounds(
        mins=(header.mins + sizes / 2)[:2],
        maxs=header.maxs[:2]
    )
    querys.append(query_bounds)


    return querys

def main():
    # path = "http://localhost:8000/autzen-classified.copc(1).laz"
    # path = "http://localhost:8000/sofi.copc.laz"
    # path = "https://s3.amazonaws.com/hobu-lidar/autzen-classified.copc.laz"
    # path = "https://s3.amazonaws.com/hobu-lidar/sofi.copc.laz"
    # path = "https://s3.amazonaws.com/hobu-lidar/montreal-2015.copc.laz"
    path = "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
    
    with CopcReader.open(path) as crdr:
        print("copc_reader_ready")
        # querys = create_query(crdr.header)
        # for i, query_bounds in enumerate(querys):
        #     resolution = None
        #     points = crdr.query(query_bounds, resolution=resolution)
        #     print("Spatial Query gave:", points)
        #     print(len(points) / crdr.header.point_count * 100);

            # new_header = laspy.LasHeader(
            #     version=crdr.header.version,
            #     point_format=crdr.header.point_format
            # )
            # new_header.offsets = crdr.header.offsets
            # new_header.scales = crdr.header.scales
            # with laspy.open(f"output_{i}.las", mode="w", header=new_header) as f:
            #     f.write_points(points)



if __name__ == '__main__':
    t0 = time.time()
    main()
    t1 = time.time()
    print("It took:", t1 - t0, " seconds")

