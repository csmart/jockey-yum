Name:		jockey
Version:	0.9.3
Release:	2%{?dist}
Summary:	Jockey driver manager

Group:		System Environment/Base
License:	GPLv2
URL:		https://launchpad.net/jockey
Source0:	http://launchpad.net/jockey/trunk/0.9.3/+download/jockey-%version.tar.gz
Patch0:     https://github.com/downloads/csmart/jockey/jockey-%version-kororaa.patch
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildArch:  noarch

BuildRequires:	python2-devel
Requires:	dbus-python pygobject2 pyxdg python-xkit python-distutils-extra python-pycurl polkit PackageKit

%description
Jockey provides a user interface and desktop integration 
for the installation and upgrade of third-party drivers.

%package kde
Summary:    KDE frontend for Jockey
Group:        Applications/System
Requires:   jockey polkit-kde PyQt4 PyKDE4
%description kde
This package provides a Qt interface for Jockey.

%package gtk
Summary: GTK frontend for Jockey
Group:        Applications/System
Requires: jockey polkit-gnome gdk-pixbuf gtk2
%description gtk
This package provides a GTK interface for Jockey.

%prep
%setup -q
%patch0 -p1

%build
%{__python} setup.py build

%configure


%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --root %{buildroot}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc

%changelog
* Sun Aug 14 2011 Chris Smart <chris@kororaa.org> 0.9.3-2
- Initial port of oslib to yum backend. 

* Sat May 7 2011 Chris Smart <chris@kororaa.org> 0.9.3-1
- Created initial spec files from README.