#!/usr/bin/perl -w
# rrd-graph.cgi -- part of the GWFL RRD-Graph Project
# $Id: rrd-graph.cgi,v 1.2 2005/11/18 06:16:46 gary Exp $

use strict;
use lib qw(/usr/lib/fifo-rrd);	# path to FIFO-RRD directory
use POSIX qw(strftime);
use graph_templates;
use template_config;
use Validate;
use RRDs;
use CGI;

my $rrdpath = '/home/rrd';			# where the RRDs will be stored
my $webroot = '/var/www/html';	# web server's docroot
my $imgpath = '/rrd-graph';			# path (relative to docroot) to graph images

my $req = new CGI;
my $v = Validate->new('A-Za-z0-9 :\/-');
my ($host, $service);

sub throwerror {
	print "<div align=\"center\">", $req->h2("@_"), "</div>",
}

print $req->header(-type => 'text/html', -expires => 'now');

if (!($host = $v->filter($req->param('host'))) || 
		!($service = $v->filter($req->param('service')))) {
	print $req->start_html(-title => "Error"),
		"<div align=\"center\">", $req->h2("@_"), "</div>",
		$req->end_html;
	exit 1;
}

my $date = strftime "%a %b %e %H:%M:%S %Z (GMT%z) %Y", localtime(time);
$date =~ s#:#\\\:#g;

mkdir "$webroot/$imgpath/$host" or throwerror 
	"Can't create $webroot/$imgpath/$host: $!" and exit 1 unless 
	(-e "$webroot/$imgpath/$host" && -w "$webroot/$imgpath/$host");

sub chchars {
	$_ = "@_";
	s#/# slash #g;
	s#:##g;
	return $_;
}

my $head = ($service eq 'all') ? "All services for $host" :
  "$service for $host";

print $req->start_html(-title => "$service on $host"),
  "<div align=\"center\">", $req->h2($head), "<br>";

my @services;

if ($service eq 'all') {
	my @groups = template_groups($host);
	foreach my $g (@groups) { 
		foreach my $svc (keys %{$graph_templates{$g}}) {
			push(@services, $svc) if (-e "$rrdpath/$host/".join('_', $host, 
				split(/\s+/, chchars($svc))).'.rrd');
  	}
	}
} else {
	push(@services, $service)
}

foreach my $fullsvc (sort @services) {
	my $escsvc = join('_', $host, split(/\s+/, chchars($fullsvc)));
	my $fullrrd = "$rrdpath/$host/$escsvc".'.rrd';

	throwerror "No such file: $fullrrd" if (!-e $fullrrd);

	my @gdata = build_template($host, $fullsvc, \%graph_templates); 

	foreach (@gdata) {
		s#DATE#$date#;
		s/RRDFILE/$fullrrd/;
		s/HOST/$host/;
	}

	my @sorted = sort keys %graph_times;
	my @times = ($service eq 'all') ? $sorted[0] : @sorted;

	foreach my $tk (@times) {
		RRDs::graph("$webroot/$imgpath/$host/$escsvc".'_'."$tk".'.png',
			"--start=${$graph_times{$tk}}[0]",
			"--end=${$graph_times{$tk}}[1]",
			@gdata);

		my $error = RRDs::error;
		throwerror $error if $error;

 		print "<a href=\"/nagios/cgi-bin/rrd-graph.cgi?host=$host&service=$fullsvc\">",
			$req->img({src => "$imgpath/$host/$escsvc".'_'."$tk".'.png'}), "</a>",
		"<br><font size=\"2\"><b>($tk ${$graph_times{$tk}}[2])</b></font><br>",
		"<br>";
	}
}

print "</div>",
	$req->end_html;

exit 0;
