# aws-inspector
This tool allows for auditing various AWS services for public access.
It will check various AWS resources defined in `Config.py` and generate a CSV of exposed services to the Internet.

### How to install
```
git clone https://github.com/jark99/aws-inspector-public.git
cd aws-inspector-public
pip install -r requirements.txt
```

### Build Requirements
- Python3
- Boto3

### Configuration
Configuration vars are handled via `Config.py`. Edit the vars as required.

```
profile_name = '<insert your default profile name>'

regions = [
'us-east-1',
'sa-east-1'
]

services = [
  'ec2',
  'elb',
  'elbv2',
  'rds'
]

output_format = "csv"
```
- **profile_name**: `AWS Profile name that is located in your ~/.aws/credentials`
- **regions**: `List of regions for the script to crawl and inspect services for`
- **services**: `List of service to check for Public IPs`. Current options are: `ec2`, `rds`, `elb`...etc`.
- **output_format**: `Defined the output format of the data, (currently a placeholder for future)`

### Running
`python vuln_detector.py --profile {insert profile}`

### Output
Dummy csv:
```
Resource Name, Service Identifier, Public IP, Ports Exposed, Security Group
ec2,alpaca, 52.200.30.22,i-0b34892ed83902j, ['tcp/1433', 'tcp/80', 'tcp/443'], sg-0b08f2213306b4850
rds,gnome-db, 52.320.56.11,i-0b34892ed83902j, ['tcp/1433', 'tcp/80'], sg-03jv389dj334
elb,oracle-lb, 52.342.45.90,i-0b34892ed83902j, ['tcp/0-65535'], sg-0e8j3mdh3gf
elb-v2,yoshi-lb, 52.2.342.4,i-0b34892ed83902j,  ['tcp/0-65535'], sg-0eb03uj4dn3804
```


### Notes
If `--profile` is not passed during Run then `default-profile` will be used in `Config.py`.

### Known Issues
1. DockerFile is a placeholder, ran into some minor issues developing on Windows host
2. CSV Writer requires a path, currently associated to Windows Hosts. Change to use OS libs for dynamic paths

### Future iterations
1. Automate further with Docker integration
2. Additional functionality to define output formats (i.e. CSV, JSON, etc.)
