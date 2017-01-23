#create plots from Nephele output using phlyoseq
#### USAGE #########

#betterplots.R <biom file> <mapping file as txt> <taxa level for plots> <HMP YES/NO>

##################################################################################
# The possiblity exitsts to add many options for producing custom graphics       #
# we could have a value for metadata colulm which would repace "TreatmentGroup"  #
# we could produce different types of output files (i.e. pdf, jpg, tiff, etc)    #
# having options to change the x axes if desired.                                #
# We could also produce different plots (i.e. diversity, PCoA, etc)              #
# This is just the plain MVP for getting this working.                           #
##################################################################################

#Get packages
suppressMessages(library('phyloseq'))
suppressMessages(library('ggplot2'))
suppressMessages(library('plyr'))
suppressMessages(library('grid'))

#generate ordered bar chart function
plot_ordered_bar<-function (physeq, x = "Sample", 
                            y = "Abundance", 
                            fill = NULL, 
                            leg_size = 0.5,
                            title = NULL) {
  require(ggplot2)
  require(phyloseq)
  require(plyr)
  require(grid)
  bb <- psmelt(physeq)
  
  samp_names <- aggregate(bb$Abundance, by=list(bb$Sample), FUN=sum)[,1]
  .e <- environment()
  bb[,fill]<- factor(bb[,fill], rev(sort(unique(bb[,fill])))) #fill to genus
  
  
  bb<- bb[order(bb[,fill]),] # genus to fill
  p = ggplot(bb, aes_string(x = x, y = y, 
                            fill = fill), 
             environment = .e, ordered = FALSE)
  p = p +geom_bar(stat = "identity", 
                  position = "stack", 
                  color = "black") 
  p = p + theme(axis.text.x = element_text(angle = -90, hjust = 0))
  if (!is.null(title)) {
    p <- p + ggtitle(title)
  }
  return(p)
}

#take command line arguments
args = commandArgs(trailingOnly=TRUE)

if (length(args)==0) {
  stop("NEPHELE ERROR: At least one argument must be supplied (input file).n", call.=FALSE)
}

biom_file <- args[1]
map_file <- args[2]
taxa_level <- args[3]
OTU_out <- "OTU_table.txt"
HMP <- args[4]

# #convert biom file to tsv
biom <- 'biom convert -i '
biom1<- ' -o OTU_table.txt --header-key taxonomy --output-metadata-id ' 
biom3 <- ' --to-tsv'
biom2 <- paste(biom, biom_file, biom1, shQuote("Consensus Lineage"), biom3, sep="")
system(biom2)

#add line to OTU_table.txt
sed_command <- 'echo "" >> OTU_table.txt'
system(sed_command)

#load files into phyloseq

cat("\nLoading biom file to phyloseq.\n")
data_to_plot <- import_qiime(otufilename = "OTU_table.txt", mapfilename = map_file, verbose=FALSE)

#merge taxa at the order rank 

#This secion of code fixes the "Rank" vs "Kingdom" issues depending on the different DBs used
ranks_in_data <- rank_names(data_to_plot)

if (is.element("Kingdom", ranks_in_data)==FALSE) {
  if ((match("Rank1", ranks_in_data))==1) {
    if(length(ranks_in_data)==6){
      colnames(tax_table(data_to_plot)) = c("Kingdom","Phylum","Class","Order","Family","Genus")
      tax_table(data_to_plot)[, "Phylum"] <- gsub("D_1__", "", tax_table(data_to_plot)[, "Phylum"])
      tax_table(data_to_plot)[, "Class"] <- gsub("D_2__", "", tax_table(data_to_plot)[, "Class"])
      tax_table(data_to_plot)[, "Order"] <- gsub("D_3__", "", tax_table(data_to_plot)[, "Order"])
      tax_table(data_to_plot)[, "Family"] <- gsub("D_4__", "", tax_table(data_to_plot)[, "Family"])
      tax_table(data_to_plot)[, "Genus"] <- gsub("D_5__", "", tax_table(data_to_plot)[, "Genus"])
    }
    else {
      colnames(tax_table(data_to_plot)) = c("Kingdom","Phylum","Class","Order","Family","Genus","Species")
      tax_table(data_to_plot)[, "Phylum"] <- gsub("D_1__", "", tax_table(data_to_plot)[, "Phylum"])
      tax_table(data_to_plot)[, "Class"] <- gsub("D_2__", "", tax_table(data_to_plot)[, "Class"])
      tax_table(data_to_plot)[, "Order"] <- gsub("D_3__", "", tax_table(data_to_plot)[, "Order"])
      tax_table(data_to_plot)[, "Family"] <- gsub("D_4__", "", tax_table(data_to_plot)[, "Family"])
      tax_table(data_to_plot)[, "Genus"] <- gsub("D_5__", "", tax_table(data_to_plot)[, "Genus"])
      tax_table(data_to_plot)[, "Species"] <- gsub("D_6__", "", tax_table(data_to_plot)[, "Species"])
    }  
  }
}

# Remap new names to the ranks_in_data variable before checking the names against the entry
ranks_in_data <- rank_names(data_to_plot)

if (length(grep(paste("^",taxa_level,"$",sep=""), ranks_in_data))==0) {
  cat("\n####################### ERROR #####################\nYour taxa level is not in the data you provided\n")
  cat("Please choose a Rank from the list below:\n\n")
  cat(rank_names(data_to_plot))
  cat("\n\nNOTE!!!! Names are case sensitive.\n\n")
  stop("NEPELE ERROR: Bad Rank Name")
}

#collapse OTU table on taxa_level for total abundance metrics and plots
#cat("\nMerging data for",taxa_level,"total abundance plots.\n")
merged_totabund <- tax_glom(data_to_plot, taxrank=taxa_level)


#create relative abundance taxa_level tables for metrics and plots
#cat("\nMerging data for",taxa_level,"relative abundance plots.\n")
relabund <- transform_sample_counts(data_to_plot, function(OTU) OTU/sum(OTU))
merged_relabund <- tax_glom(relabund, taxrank = taxa_level)

#create heatmap if there is more than one sample in the OTU table
#the second line in the if statment renames the title of the x-axis
#total abundance heatmap is also available
number_samples <- dim(sample_data(merged_totabund))[1]
num_taxa <- dim(tax_table(merged_relabund))[1]

num_samples <- dim(sample_data(data_to_plot))[1]

#if species level plots are going to be made. 
if (((is.element("Species", ranks_in_data))==TRUE) & (taxa_level == "Species")) {
  Gen_spe_names <- c("Genus", "Species")
  Gen_spe_labels_rel <- apply(tax_table(merged_relabund)[, Gen_spe_names], 1, paste, sep="", collapse="_")
  tax_table(merged_relabund) <- cbind(tax_table(merged_relabund), Genus_species=Gen_spe_labels_rel)
  Gen_spe_labels_tot <- apply(tax_table(merged_totabund)[, Gen_spe_names], 1, paste, sep="", collapse="_")
  tax_table(merged_totabund) <- cbind(tax_table(merged_totabund), Genus_species=Gen_spe_labels_tot)
  taxa_level <- "Genus_species"
}

if ((num_samples > 2) & (num_samples < 250) & (num_taxa < 500) & (taxa_level != "Genus_species")) {
#  heat_plot_total <- plot_heatmap(merged_totabund, "NMDS", "bray", "X.SampleID", taxa_level)
  heat_plot_relative <- plot_heatmap(merged_relabund, "NMDS", "bray", "X.SampleID", taxa_level, max.label = 500)
  heat_plot_relative <- heat_plot_relative + theme(axis.text.x = element_text(size =20), axis.text.y = element_text(size=20))
  heat_plot_relative$scales$scales[[1]]$name <- "SampleID"
  if ((num_samples >= 500) | (num_taxa >= 500)) {
    cat("\n\nNEPHELE WARNING: There are over 500 taxa or samples in this graph. \nAxis Lables have been removed from the heatmap due to size limits.\n\n")
  }
} else if (num_samples < 2) {
  cat("\n\nNEPHELE WARNING: Too few samples for a heatmap. Heatmaps require 3 or more samples. No heatmap generated. \n\n")
} else { 
  cat("\n\nNEPHELE WARNING: Too many samples or taxa for a heatmap. No heatmap generated. \n\n")
}

#Ordered bars plots 
#taxa_image <- plot_ordered_bar(merged, x="X.SampleID",fill = taxa_level)
#taxa_image_ordered_total <- plot_ordered_bar(merged_totabund, x="X.SampleID",fill = taxa_level)
if (taxa_level != "Genus_species") {
  taxa_image_ordered_relative <- plot_ordered_bar(merged_relabund, x="X.SampleID",fill = taxa_level)
}
#Not Orderd bar plots and standard phyloseq colors
#taxa_image_total <- plot_bar(merged_totabund, x="X.SampleID",fill = taxa_level)
if (taxa_level != "Genus_species") {
  taxa_image_relative <- plot_bar(merged_relabund, x="X.SampleID",fill = taxa_level)
}

#no facet grids if using plots for HMP as they don't have different TreatmentGroups
if ((HMP == "NO") & (taxa_level != "Genus_species")) {
  TG_names <- sample_data(data_to_plot)[,"TreatmentGroup"]
  num_of_TGs <- length(unique(TG_names$TreatmentGroup))
  if (num_of_TGs > 1) {
    #facet by taxanomic rank
    #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
    taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom", text = element_text(size=20)) + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")
    # facet by treatment group
    #taxa_final_total_TG <- taxa_image_ordered_total + facet_grid(~TreatmentGroup,scales="free",drop=TRUE) + theme(legend.position="bottom") + ggtitle("Total OTU Counts")
    taxa_final_rel_TG <- taxa_image_ordered_relative + facet_grid(~TreatmentGroup,scales="free",drop=TRUE) + theme(legend.position="bottom", text = element_text(size=20)) + ggtitle("Relative OTU Counts") + xlab("SampleID")
  } else {
    #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
    taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom", text = element_text(size=20)) + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")
    #only needed if doing facet with TreatmentGroup col
   # taxa_final <- taxa_image + geom_bar(aes_string(color=taxa_level,fill=taxa_level),stat="identity", position="stack") + theme(legend.position="bottom")
 }
}
if (HMP == "YES")  {
  #taxa_final_total <- taxa_image_total + theme(legend.position="bottom") + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Total OTU Counts")
  taxa_final_relative <- taxa_image_relative + theme(legend.position="bottom", text = element_text(size=20)) + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Relative OTU Counts") + xlab("SampleID")
  
  #taxa_final <- taxa_image + geom_bar(aes_string(color=taxa_level,fill=taxa_level),stat="identity", position="stack") + theme(legend.position="bottom") 
}

#save images
#sets up folders and file names and paths
if (HMP == "YES") {
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps", showWarnings = FALSE)
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/mini_barplots" ,showWarnings = FALSE)
  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/heatmaps" ,showWarnings = FALSE)

  HMP_file <- strsplit(map_file, "/")[[1]]
  HMP_file
  
  heat_name <- paste(noquote(HMP_file[1]),"_heat_map_relative_abundance_",taxa_level,".png", sep="")
  heat_path <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps","heatmaps",heat_name, sep="/")
  
  #taxa_name_total <- paste(noquote(HMP_file[1]),"_taxa_plot_total_abundance_",taxa_level,".png",sep="")
  #taxa_path_total <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps",taxa_name_total,sep="/")
  
  taxa_name_relative <- paste(noquote(HMP_file[1]),"_taxa_plot_relative_abundance_",taxa_level,".png",sep="")
  taxa_path_relative <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps","mini_barplots",taxa_name_relative,sep="/")

  taxa_OTU_name <- paste(noquote(HMP_file[1]),"_taxa_plot_to_100_OTUs_",taxa_level,".png",sep="")
  taxa_OTU_path <- paste("HMP_compare_results","HMP_taxa_plots_and_heatmaps","mini_barplots",taxa_OTU_name,sep="/")

  #save tables
  Phylum = 2
  Class = 3
  Order = 4
  Family = 5
  Genus = 6
  Species = 7

  dir.create("HMP_compare_results/HMP_taxa_plots_and_heatmaps/taxa_count_tables", showWarnings=FALSE)
  table <- otu_table(merged_totabund)
  rownames(table)=tax_table(merged_totabund)[,taxa_level]
  table_name <- paste(noquote(HMP_file[1]),"_taxa_counts_",taxa_level,".csv", sep="")
  table_path <- paste("HMP_compare_results/HMP_taxa_plots_and_heatmaps/taxa_count_tables",table_name, sep = "/")
  write.csv(table, file = table_path)
}

#different paths if these are not done duing the HMP pipeline
if (HMP == "NO") {
  dir.create("taxa_plots_and_heatmaps" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/stacked_barplots" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/mini_barplots" ,showWarnings = FALSE)
  dir.create("taxa_plots_and_heatmaps/heatmaps" ,showWarnings = FALSE)
  
  heat_name <- paste("heat_map_relative_abundance_",taxa_level,".png", sep="")
  heat_path <- paste("taxa_plots_and_heatmaps/heatmaps",heat_name, sep="/")

  #taxa_name_total <- paste("taxa_plot_total_abundance_",taxa_level,".png",sep="")
  #taxa_path_total <- paste("taxa_plots_and_heatmaps",taxa_name_total,sep="/")
  
  #taxa_name_total_TG <- paste("taxa_plot_total_abundance_by_TreatmentGroup_",taxa_level,".png",sep="")
  #taxa_path_total_TG <- paste("taxa_plots_and_heatmaps",taxa_name_total_TG,sep="/")

  taxa_name_relative <- paste("taxa_plot_relative_abundance_",taxa_level,".png",sep="")
  taxa_path_relative <- paste("taxa_plots_and_heatmaps/mini_barplots",taxa_name_relative,sep="/")

  taxa_OTU_name <- paste("taxa_plot_top_100_OTUs_",taxa_level,".png",sep="")
  taxa_OTU_path <- paste("taxa_plots_and_heatmaps/mini_barplots",taxa_OTU_name,sep="/")

  taxa_name_relative_TG <- paste("taxa_plot_relative_abundance_by_TreatmentGroup_",taxa_level,".png",sep="")
  taxa_path_relative_TG <- paste("taxa_plots_and_heatmaps/stacked_barplots",taxa_name_relative_TG,sep="/")

  #save tables
  Phylum = 2
  Class = 3
  Order = 4
  Family = 5
  Genus = 6
  Species = 7

  dir.create("taxa_plots_and_heatmaps/taxa_count_tables", showWarnings=FALSE)
  table <- otu_table(merged_totabund)
  rownames(table)=tax_table(merged_totabund)[,taxa_level]
  table_name <- paste("taxa_counts_",taxa_level,".csv", sep="")
  table_path <- paste("taxa_plots_and_heatmaps/taxa_count_tables",table_name, sep = "/")
  write.csv(table, file = table_path)
}

#--------------------------   PLOTS  -----------------------------------------------------------

#set Width for all tax plots
graph_width_tax <- dim(sample_data(merged_totabund))[1]
num_mini_plots <- dim(tax_table(merged_relabund))[1]

#cat("\nNumber of samples: ",graph_width_tax,"\n\n")
#cat("\nNumber of mini plots: ",num_mini_plots,"\n")

if (graph_width_tax < 10) {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*400)
} else if((graph_width_tax > 50) & (graph_width_tax < 99)) {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*320)
} else if((graph_width_tax > 100) & (num_mini_plots < 100)) {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*260)
} else {
  graph_width_tax <- ((dim(sample_data(merged_totabund))[1])*300)
}

#set width for heat
graph_width_heat <- dim(sample_data(merged_totabund))[1]

if (graph_width_heat < 10) {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*100)
} else if((graph_width_heat > 50) & (graph_width_heat < 99)) {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*75)
} else if(graph_width_heat > 100) {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*50)
} else {
  graph_width_heat <- ((dim(sample_data(merged_totabund))[1])*60)
}

#set minimums
if (graph_width_heat < 1700) {
  graph_width_heat <- 1700
}

if (graph_width_tax < 4000) {
  graph_width_tax <- 4000
}


# set height for heat map
graph_height_heat <- ((dim(tax_table(merged_totabund))[1])*45)

if (graph_height_heat < 1200) {
  graph_height_heat <- 1200
} else {
  graph_height_heat <- ((dim(tax_table(merged_totabund))[1])*45)
}

if ((num_samples > 2) & (num_samples < 250) & (num_taxa < 500) & (taxa_level != "Genus_species")) {
  print({
    png(filename=heat_path, width=graph_width_heat, height=graph_height_heat, units="px",res=150)
    heat_plot_relative
  })
  garbage <- dev.off()
}

#set height for taxa plots
graph_height_tax <- (num_samples*92)

if (graph_height_tax < 3700) {
  graph_height_tax <- 3700
} else {
  graph_height_tax <- ((dim(tax_table(merged_totabund))[1])*92)
}

#cat("Heat Width",graph_width_heat,"\n\n")
#cat("number of taxa: ",dim(tax_table(merged_totabund))[1])

#cat("Graph Width",graph_width_tax)


# png(filename=taxa_path_total, width=(dim(sample_data(merged_totabund))[1])*1000, height=graph_height_tax, units="px",res=300)
# taxa_final_total
# garbage <- dev.off()

#This just doesn't scale to fit properly. 
#ggsave("test.pdf", plot = taxa_final_rel_TG, dpi = 300)

if ((HMP == "NO") & (taxa_level != "Genus_species")) {
  if (num_of_TGs > 1) {
    graph_width_tax_TG <- (graph_width_tax/3)
    graph_height_tax_TG <- (graph_height_tax/4)
    if (graph_height_tax_TG > 4500) {
      graph_height_tax_TG <- 4500
    }
    if (graph_height_tax_TG < 1500) {
      graph_height_tax_TG <- 1500
    }
    if (graph_width_tax_TG < 2000) {
      graph_width_tax_TG <- (num_taxa*60)
    }
    if (graph_width_tax_TG < 2400) {
      graph_width_tax_TG <- 2400
    }
    if (graph_width_tax_TG > 25000) {
      cat("\nNEPHELE WARNING: Your", taxa_level, "Phyloseq stacked barplot was too large to save. No stacked barplot generated\n")
    } else {  
      print({
        png(filename=taxa_path_relative_TG, width=graph_width_tax_TG, height=graph_height_tax_TG, units="px",res=150)
        taxa_final_rel_TG
      })
      garbage <- dev.off()
    }
  }
}

#get top 1 percent of data not recommended by phyloseq authors
# top_99_pct <- filter_taxa(data_to_plot, function(x) sort(sum(x)) > (0.99*length(x)), TRUE)

if ((num_taxa > 140) | (graph_width_tax > 25000))  {
  cat("\nNEPHELE WARNING: Your", taxa_level, "Phyloseq mini barplot was too large to save. Graphing top 100 OTUs only for mini barplot. \nRaw OTU counts can be found in the tables for you to plot on your own. \nStandard QIIME plots can be found in the core_diversity directory.", "\n\n")
  Top_OTUs <- names(sort(taxa_sums(data_to_plot),TRUE)[1:100])
  top_OTU <- prune_taxa(Top_OTUs, data_to_plot)
  relabund <- transform_sample_counts(top_OTU, function(OTU) OTU/sum(OTU))
  merged_OTU <- tax_glom(relabund, taxrank=taxa_level)
  taxa_image_OTU <- plot_bar(merged_OTU, x="X.SampleID",fill = taxa_level)
  taxa_final_OTU <- taxa_image_OTU + theme(legend.position="bottom", text = element_text(size = 20), axis.text.x = element_text(size =20), axis.text.y = element_text(size=20)) + facet_wrap(as.formula(paste("~", taxa_level)),scales="free",drop=TRUE) + ggtitle("Top 100 OTUs - Relative Counts") + xlab("SampleID")
  if (num_taxa > 90) {
    graph_width_tax_OTU <- graph_width_tax
  } else {
    graph_width_tax_OTU <- (graph_width_tax/2)  
  }  
  graph_height_tax_OTU <- graph_height_tax
  if (graph_width_tax_OTU > 25000) {
    cat("\nNEPHELE WARNING: Your", taxa_level, "Phyloseq mini barplot was too large to save. No mini barplot generated\n")
    quit(save="no",status=0)
  } else if (taxa_level != "Genus_species") {
    print({
    png(filename=taxa_OTU_path, width=graph_width_tax_OTU, height=graph_height_tax_OTU, units="px",res=150)
    taxa_final_OTU    
    })
    garbage <- dev.off()
    cat("\nYour",taxa_level,"plots have been created and saved.\n\n")
    quit(save="no",status=0)
  } else {
    quit(save="no",status=0)
  }
}

if (taxa_level != "Genus_species") {
  print({
  png(filename=taxa_path_relative, width=graph_width_tax, height=graph_height_tax, units="px",res=150)
  taxa_final_relative
  })
  garbage <- dev.off()
}

cat("\nYour",taxa_level,"plots have been created and saved.\n\n")
# if (num_of_TGs > 1) {
#   print({
#     png(filename=taxa_path_total_TG, width=(dim(sample_data(merged_totabund))[1])*1000, height=graph_height_tax, units="px",res=300)
#     taxa_final_total_TG
#   })
#   garbage <- dev.off()
# }