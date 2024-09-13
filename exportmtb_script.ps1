for ($i = 0; $i -le 4; $i++) {
    for ($j = 0; $j -le 2; $j++) {
        for ($k = 0; $k -le 9; $k++) {

            python ./Scripts/mtb_exporter.py --recording_subject $i --recording_type $j --recording_class $k
        }

    }

}