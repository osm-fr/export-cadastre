<?php

umask(002);

// Set it to true when you have a doubt about Qadastre output
$do_we_log=false;

// Read and set config variables
$config_handle = fopen("../config", "r");
if ($config_handle) {
    while (($line = fgets($config_handle)) !== false) {
        $args = explode('=', $line, 2);
        $var_name = trim($args[0]);
        $$var_name = trim($args[1]);
    }
    fclose($config_handle);
} else {
    print("config file not found");
    exit(0);
}

// Read department list
$dep_array=array();
$dep_list_handle = fopen($data_dir . "/dep-liste.txt", "r");
if ($dep_list_handle) {
    while (($line = fgets($dep_list_handle)) !== false) {
        $args = explode(' ', $line, 2);
        $dep_code = trim($args[0]);
        $dep_name = trim(str_replace('"','', $args[1]));
        array_push($dep_array, array(
            "id" => $dep_code,
            "name" => $dep_name)
        );
    }
    fclose($dep_list_handle);
} else {
    print("department list file not found");
    exit(0);
}

