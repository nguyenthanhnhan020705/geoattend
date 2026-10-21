def purge_locations(conn,now):
    with conn.transaction():
        return conn.execute('UPDATE geoattend.office_locations SET point=NULL,accuracy_m=NULL,purged_at=%s WHERE expires_at<=%s AND purged_at IS NULL',(now,now)).rowcount
